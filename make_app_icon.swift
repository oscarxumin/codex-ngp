import AppKit
import CoreGraphics
import Foundation

let sourcePath = "/Users/oscarngp/Desktop/codex组队/source_logo_for_icon.png"
let outputPath = "/Users/oscarngp/Desktop/codex组队/app_icon_1024.png"
let size = 1024

guard let image = NSImage(contentsOfFile: sourcePath),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff) else {
    fatalError("Cannot read source image")
}

let width = bitmap.pixelsWide
let height = bitmap.pixelsHigh
var minX = width
var minY = height
var maxX = 0
var maxY = 0

for y in 0..<height {
    for x in 0..<width {
        guard let color = bitmap.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB) else { continue }
        let r = color.redComponent
        let g = color.greenComponent
        let b = color.blueComponent
        let isWhiteBackground = r > 0.93 && g > 0.93 && b > 0.93 && abs(r - g) < 0.04 && abs(g - b) < 0.04
        if !isWhiteBackground {
            minX = min(minX, x)
            minY = min(minY, y)
            maxX = max(maxX, x)
            maxY = max(maxY, y)
        }
    }
}

if minX >= maxX || minY >= maxY {
    minX = 0
    minY = 0
    maxX = width - 1
    maxY = height - 1
}

let contentWidth = maxX - minX + 1
let contentHeight = maxY - minY + 1
let padding = max(4, Int(Double(max(contentWidth, contentHeight)) * 0.015))
minX = max(0, minX - padding)
minY = max(0, minY - padding)
maxX = min(width - 1, maxX + padding)
maxY = min(height - 1, maxY + padding)

let cropRect = NSRect(x: minX, y: height - maxY - 1, width: maxX - minX + 1, height: maxY - minY + 1)
guard let cropped = bitmap.cgImage?.cropping(to: CGRect(x: cropRect.origin.x, y: cropRect.origin.y, width: cropRect.width, height: cropRect.height)) else {
    fatalError("Cannot crop image")
}

let canvas = NSImage(size: NSSize(width: size, height: size))
canvas.lockFocus()
NSColor.white.setFill()
NSRect(x: 0, y: 0, width: size, height: size).fill()

let cropAspect = CGFloat(cropped.width) / CGFloat(cropped.height)
let targetInset: CGFloat = 16
let maxTarget = CGFloat(size) - targetInset * 2
var drawWidth = maxTarget
var drawHeight = maxTarget / cropAspect
if drawHeight > maxTarget {
    drawHeight = maxTarget
    drawWidth = maxTarget * cropAspect
}
let drawRect = NSRect(
    x: (CGFloat(size) - drawWidth) / 2,
    y: (CGFloat(size) - drawHeight) / 2,
    width: drawWidth,
    height: drawHeight
)
NSGraphicsContext.current?.imageInterpolation = .high
NSImage(cgImage: cropped, size: NSSize(width: cropped.width, height: cropped.height)).draw(in: drawRect)
canvas.unlockFocus()

guard let pngTiff = canvas.tiffRepresentation,
      let pngBitmap = NSBitmapImageRep(data: pngTiff),
      let pngData = pngBitmap.representation(using: .png, properties: [:]) else {
    fatalError("Cannot write PNG")
}
try pngData.write(to: URL(fileURLWithPath: outputPath))
print("wrote \(outputPath)")
