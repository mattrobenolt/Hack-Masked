import Foundation
import CoreGraphics
import CoreText
import ImageIO

let args = CommandLine.arguments
guard args.count >= 3 else {
    print("usage: render <font> <out.png> [size]")
    exit(1)
}
let fontPath = args[1]
let outPath = args[2]
let size = args.count > 3 ? CGFloat(Double(args[3]) ?? 28) : 28

let font: CTFont
if fontPath.hasSuffix(".ttf") || fontPath.hasSuffix(".otf") {
    let url = URL(fileURLWithPath: fontPath)
    guard let provider = CGDataProvider(url: url as CFURL), let cgFont = CGFont(provider) else {
        print("cannot load font"); exit(1)
    }
    font = CTFontCreateWithGraphicsFont(cgFont, size, nil, nil)
} else {
    font = CTFontCreateWithName(fontPath as CFString, size, nil)
}
print("font:", CTFontCopyPostScriptName(font) as String)

let samples = [
    "ghp_aB3dEFGHiJ7kLmN0pQr",
    "GITHUB_TOKEN=xY7kQ2pLm9ZtR4vB",
    "Authorization: Bearer aZ81kPq0xT7vLm3N",
    "AKIAZBCE3YZFTLJZKB2JWAF653TBXN5K",
    "MONKEY=banana",
    "SORT_KEY=modified_date",
    "ghp_import",
    "sk-ant-api03-qp8YJHVARCfcAGRVedv7d5hkgJTs",
]
let width = 1500
let lineHeight = Int(size * 1.55)
let height = lineHeight * samples.count + 30
let cs = CGColorSpaceCreateDeviceRGB()
let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8,
                    bytesPerRow: 0, space: cs,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
ctx.setFillColor(CGColor(red: 0.05, green: 0.05, blue: 0.05, alpha: 1))
ctx.setShouldAntialias(true)
ctx.setShouldSmoothFonts(true)

for (i, text) in samples.enumerated() {
    let attrs = [kCTFontAttributeName: font] as CFDictionary
    let attrString = CFAttributedStringCreate(nil, text as CFString, attrs)!
    let line = CTLineCreateWithAttributedString(attrString)
    let y = CGFloat(height - 20 - i * lineHeight)
    ctx.textPosition = CGPoint(x: 20, y: y)
    CTLineDraw(line, ctx)
}

guard let image = ctx.makeImage() else { print("no image"); exit(1) }
let outURL = URL(fileURLWithPath: outPath)
guard let dest = CGImageDestinationCreateWithURL(outURL as CFURL, CFStringCreateWithCString(nil, "public.png", CFStringBuiltInEncodings.UTF8.rawValue)!, 1, nil) else {
    print("no dest"); exit(1)
}
CGImageDestinationAddImage(dest, image, nil)
if !CGImageDestinationFinalize(dest) { print("write failed"); exit(1) }
print("wrote \(outPath)")
