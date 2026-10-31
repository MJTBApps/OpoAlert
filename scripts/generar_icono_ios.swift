// Dibuja el icono de iOS (1024 × 1024) con el mismo diseño que el de Android
// (app/src/main/res/drawable/ic_launcher_*.xml): boletín blanco y aviso ámbar
// con campana sobre un degradado azul. iOS redondea las esquinas por su cuenta.
//
//   swiftc scripts/generar_icono_ios.swift -o /tmp/icono && /tmp/icono ios/OpoAlert/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
import AppKit

let size = 1024
// Android dibuja en una ventana de 108 unidades; iOS usa la zona central de 80.
let origin: CGFloat = 14, span: CGFloat = 80
func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
    CGPoint(x: (x - origin) / span * CGFloat(size), y: CGFloat(size) - (y - origin) / span * CGFloat(size))
}
func len(_ v: CGFloat) -> CGFloat { v / span * CGFloat(size) }
func color(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}

let space = CGColorSpace(name: CGColorSpace.sRGB)!
let ctx = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                    bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!

// Fondo: degradado de arriba a la izquierda a abajo a la derecha.
let gradient = CGGradient(colorsSpace: space, colors: [color(0x2563EB), color(0x1E3A8A)] as CFArray,
                          locations: [0, 1])!
ctx.drawLinearGradient(gradient, start: CGPoint(x: 0, y: size), end: CGPoint(x: size, y: 0), options: [])

func roundedRect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ r: CGFloat, _ fill: CGColor) {
    let topLeft = p(x, y + h)
    let rect = CGRect(x: topLeft.x, y: topLeft.y, width: len(w), height: len(h))
    ctx.addPath(CGPath(roundedRect: rect, cornerWidth: len(r), cornerHeight: len(r), transform: nil))
    ctx.setFillColor(fill)
    ctx.fillPath()
}
func circle(_ cx: CGFloat, _ cy: CGFloat, _ r: CGFloat, _ fill: CGColor) {
    let c = p(cx, cy)
    ctx.addEllipse(in: CGRect(x: c.x - len(r), y: c.y - len(r), width: 2 * len(r), height: 2 * len(r)))
    ctx.setFillColor(fill)
    ctx.fillPath()
}

roundedRect(34, 30, 36, 50, 4, color(0x1E3A8A, 0.2))   // sombra
roundedRect(34, 28, 34, 48, 3, color(0xFFFFFF))         // boletín
roundedRect(37.5, 33, 27, 6, 1.5, color(0x1D4ED8))      // cabecera
for (y, w) in [(44, 24), (50, 24), (56, 17), (62, 12)] as [(CGFloat, CGFloat)] {
    roundedRect(39, y, w, 2.6, 0, color(0xBFDBFE))      // líneas de texto
}
circle(66, 70, 14, color(0xFFFFFF))                      // aro
circle(66, 70, 12, color(0xF59E0B))                      // aviso

// Campana (misma silueta que el vector de Android, en coordenadas absolutas).
let bell = CGMutablePath()
bell.move(to: p(66, 62.5))
bell.addCurve(to: p(59.7, 68.9), control1: p(62.2, 62.5), control2: p(59.7, 65.4))
bell.addLine(to: p(59.7, 72.6))
bell.addCurve(to: p(57.5, 76.5), control1: p(59.7, 74.2), control2: p(58.9, 75.4))
bell.addLine(to: p(74.5, 76.5))
bell.addCurve(to: p(72.3, 72.6), control1: p(73.1, 75.4), control2: p(72.3, 74.2))
bell.addLine(to: p(72.3, 68.9))
bell.addCurve(to: p(66, 62.5), control1: p(72.3, 65.4), control2: p(69.8, 62.5))
bell.closeSubpath()
bell.move(to: p(63.7, 77.6))
bell.addLine(to: p(68.3, 77.6))
bell.addCurve(to: p(66, 79.9), control1: p(67.9, 79.1), control2: p(67.1, 79.9))
bell.addCurve(to: p(63.7, 77.6), control1: p(64.9, 79.9), control2: p(64.1, 79.1))
bell.closeSubpath()
ctx.addPath(bell)
ctx.setFillColor(color(0xFFFFFF))
ctx.fillPath()

let output = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon-1024.png")
let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
try! rep.representation(using: .png, properties: [:])!.write(to: output)
print("Icono escrito en \(output.path)")
