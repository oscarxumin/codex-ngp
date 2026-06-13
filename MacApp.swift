import Cocoa
import LocalAuthentication
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var exporters: [ReportExporter] = []

    func applicationDidFinishLaunching(_ notification: Notification) {
        let config = WKWebViewConfiguration()
        let store = WKWebsiteDataStore.default()
        config.websiteDataStore = store
        config.userContentController.add(self, name: "exportFile")

        webView = WKWebView(frame: .zero, configuration: config)
        webView.setValue(false, forKey: "drawsBackground")

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1220, height: 780),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "新天地棋牌组队系统"
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)

        webView.loadHTMLString("<main style='font-family:-apple-system;padding:48px'><h1>新天地棋牌组队系统</h1><p>正在等待 Touch ID 解锁...</p></main>", baseURL: nil)
        authenticateAndLoadApp()
    }

    private func authenticateAndLoadApp() {
        let context = LAContext()
        context.localizedReason = "使用 Touch ID 解锁新天地棋牌组队系统"
        var error: NSError?
        let biometricPolicy: LAPolicy = .deviceOwnerAuthenticationWithBiometrics
        let fallbackPolicy: LAPolicy = .deviceOwnerAuthentication
        let policy = context.canEvaluatePolicy(biometricPolicy, error: &error) ? biometricPolicy : fallbackPolicy

        context.evaluatePolicy(policy, localizedReason: "解锁新天地棋牌组队系统") { [weak self] success, authError in
            DispatchQueue.main.async {
                guard success else {
                    self?.showAlert("解锁失败", authError?.localizedDescription ?? "未通过系统验证。")
                    NSApp.terminate(nil)
                    return
                }
                self?.loadApp()
            }
        }
    }

    private func loadApp() {
        if let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "app") {
            webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        } else {
            webView.loadHTMLString("<h1>启动失败</h1><p>没有找到界面文件。</p>", baseURL: nil)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "exportFile",
              let payload = message.body as? [String: Any],
              let type = payload["type"] as? String,
              let filename = payload["filename"] as? String else {
            showAlert("导出失败", "没有收到有效的报表数据。")
            return
        }

        if let text = payload["text"] as? String {
            do {
                let url = uniqueBackupURL(named: filename)
                try text.data(using: .utf8)?.write(to: url)
                showAlert("导出成功", "文件已保存到桌面/codex组队/backup：\n\(url.lastPathComponent)")
            } catch {
                showAlert("导出失败", error.localizedDescription)
            }
        } else if let html = payload["html"] as? String {
            let exporter = ReportExporter(
                type: type,
                filename: filename,
                html: html,
                saveURLProvider: uniqueDesktopURL(named:),
                completion: { [weak self] exporter, result in
                    self?.exporters.removeAll { $0 === exporter }
                    switch result {
                    case .success(let url):
                        self?.showAlert("导出成功", "文件已保存到桌面：\n\(url.lastPathComponent)")
                    case .failure(let error):
                        self?.showAlert("导出失败", error.localizedDescription)
                    }
                }
            )
            exporters.append(exporter)
            exporter.start()
        } else {
            showAlert("导出失败", "没有收到报表内容。")
        }
    }

    private func uniqueDesktopURL(named filename: String) -> URL {
        let desktop = FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first!
        return uniqueURL(in: desktop, named: filename)
    }

    private func uniqueBackupURL(named filename: String) -> URL {
        let desktop = FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first!
        let backup = desktop.appendingPathComponent("codex组队").appendingPathComponent("backup")
        try? FileManager.default.createDirectory(at: backup, withIntermediateDirectories: true)
        return uniqueURL(in: backup, named: filename)
    }

    private func uniqueURL(in directory: URL, named filename: String) -> URL {
        let baseURL = directory.appendingPathComponent(filename)
        if !FileManager.default.fileExists(atPath: baseURL.path) {
            return baseURL
        }

        let ext = baseURL.pathExtension
        let stem = baseURL.deletingPathExtension().lastPathComponent
        let stamp = Int(Date().timeIntervalSince1970)
        if ext.isEmpty {
            return directory.appendingPathComponent("\(stem)-\(stamp)")
        }
        return directory.appendingPathComponent("\(stem)-\(stamp).\(ext)")
    }

    private func showAlert(_ title: String, _ message: String) {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.messageText = title
            alert.informativeText = message
            alert.alertStyle = title.contains("失败") ? .warning : .informational
            alert.runModal()
        }
    }
}

final class ReportExporter: NSObject, WKNavigationDelegate {
    private let type: String
    private let filename: String
    private let html: String
    private let saveURLProvider: (String) -> URL
    private let completion: (ReportExporter, Result<URL, Error>) -> Void
    private let webView: WKWebView

    init(
        type: String,
        filename: String,
        html: String,
        saveURLProvider: @escaping (String) -> URL,
        completion: @escaping (ReportExporter, Result<URL, Error>) -> Void
    ) {
        self.type = type
        self.filename = filename
        self.html = html
        self.saveURLProvider = saveURLProvider
        self.completion = completion
        self.webView = WKWebView(frame: NSRect(x: 0, y: 0, width: 980, height: 1400))
        super.init()
        self.webView.navigationDelegate = self
    }

    func start() {
        webView.loadHTMLString(wrappedHTML(), baseURL: nil)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            self.export()
        }
    }

    private func export() {
        webView.evaluateJavaScript("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)") { value, _ in
            let rawHeight: CGFloat
            if let number = value as? NSNumber {
                rawHeight = CGFloat(truncating: number)
            } else if let double = value as? Double {
                rawHeight = CGFloat(double)
            } else if let int = value as? Int {
                rawHeight = CGFloat(int)
            } else {
                rawHeight = 1400
            }
            let height = min(max(800, rawHeight), 20000)
            self.webView.setFrameSize(NSSize(width: 980, height: height))
            if self.type == "pdf" {
                self.exportPDF(height: height)
            } else {
                self.exportPNG(height: height)
            }
        }
    }

    private func exportPDF(height: CGFloat) {
        let config = WKPDFConfiguration()
        config.rect = CGRect(x: 0, y: 0, width: 980, height: height)
        webView.createPDF(configuration: config) { result in
            switch result {
            case .success(let data):
                self.write(data: data, extension: "pdf")
            case .failure(let error):
                self.completion(self, .failure(error))
            }
        }
    }

    private func exportPNG(height: CGFloat) {
        let config = WKSnapshotConfiguration()
        config.rect = CGRect(x: 0, y: 0, width: 980, height: height)
        webView.takeSnapshot(with: config) { image, error in
            if let error {
                self.completion(self, .failure(error))
                return
            }
            guard let image,
                  let tiff = image.tiffRepresentation,
                  let bitmap = NSBitmapImageRep(data: tiff),
                  let data = bitmap.representation(using: .png, properties: [:]) else {
                self.completion(self, .failure(NSError(domain: "ReportExporter", code: 1, userInfo: [NSLocalizedDescriptionKey: "PNG 文件生成失败。"])))
                return
            }
            self.write(data: data, extension: "png")
        }
    }

    private func write(data: Data, extension ext: String) {
        let outputName = filename.hasSuffix(".\(ext)") ? filename : "\(filename).\(ext)"
        do {
            let url = saveURLProvider(outputName)
            try data.write(to: url)
            completion(self, .success(url))
        } catch {
            completion(self, .failure(error))
        }
    }

    private func wrappedHTML() -> String {
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body { margin: 0; background: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
            .report-shell { background: #fff; color: #121826; padding: 30px; width: 920px; box-sizing: border-box; }
            .report-title { text-align: center; font-size: 34px; font-weight: 800; margin: 0; }
            .report-dates { text-align: center; color: #4d5562; font-size: 22px; margin: 14px 0 30px; }
            .report-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-bottom: 32px; }
            .report-stat { border: 1px solid #dfe3e8; border-radius: 28px; padding: 28px 34px; background: #fbfcfe; }
            .report-stat-label { color: #5d6673; font-size: 18px; margin-bottom: 18px; }
            .report-stat-value { font-size: 40px; font-weight: 800; line-height: 1; }
            .report-date-section { margin-top: 28px; }
            .report-date-heading { font-size: 28px; font-weight: 800; margin: 0 0 18px; }
            .report-entry { border: 1px solid #e1e5ea; border-radius: 24px; background: #fbfcfe; padding: 26px 32px; margin-bottom: 22px; }
            .report-entry-customers { font-size: 22px; font-weight: 800; margin-bottom: 18px; }
            .report-entry-line { color: #4d5562; font-size: 20px; margin: 8px 0; }
          </style>
        </head>
        <body>
        \(html)
        </body>
        </html>
        """
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()
