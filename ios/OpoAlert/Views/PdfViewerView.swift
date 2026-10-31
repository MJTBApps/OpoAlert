import OpoAlertCore
import PDFKit
import SwiftUI

/// El PDF oficial dentro de la app, con PDFKit. Se descarga a memoria (no queda en
/// «Archivos»); si el enlace no es un PDF, se abre fuera como antes.
struct PdfViewerView: View {
    let url: URL
    let title: String
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @State private var document: PDFDocument?
    @State private var failed = false

    var body: some View {
        NavigationStack {
            Group {
                if let document {
                    PdfKitView(document: document, startPage: OfficialDocument.startPage(url.absoluteString))
                        .ignoresSafeArea(edges: .bottom)
                } else if failed {
                    VStack(spacing: 16) {
                        Text("No se ha podido cargar el PDF dentro de la app.")
                            .multilineTextAlignment(.center)
                        Button("Abrir en el navegador") { openURL(url) }
                            .buttonStyle(.borderedProminent)
                            .tint(Color(hex: 0xFE4559))
                    }
                    .padding(30)
                } else {
                    ProgressView("Cargando el PDF oficial…")
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(hex: 0xE9EEF5))
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cerrar") { dismiss() }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        openURL(url)
                    } label: {
                        Image(systemName: "safari")
                    }
                    .accessibilityLabel("Abrir en el navegador")
                }
            }
        }
        .task { await load() }
    }

    private func load() async {
        var request = URLRequest(url: url, timeoutInterval: 30)
        request.setValue("OpoAlert-iOS/1.0", forHTTPHeaderField: "User-Agent")
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode),
                  http.url?.scheme == "https" else {
                failed = true
                return
            }
            guard OfficialDocument.looksLikePdf(data) else {
                // Es una página web: se abre fuera.
                openURL(url)
                dismiss()
                return
            }
            if let pdf = PDFDocument(data: data) { document = pdf } else { failed = true }
        } catch {
            failed = true
        }
    }
}

private struct PdfKitView: UIViewRepresentable {
    let document: PDFDocument
    let startPage: Int

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.backgroundColor = UIColor(red: 0.91, green: 0.93, blue: 0.96, alpha: 1)
        view.document = document
        if let page = document.page(at: min(startPage, document.pageCount) - 1) {
            DispatchQueue.main.async { view.go(to: page) }
        }
        return view
    }

    func updateUIView(_ view: PDFView, context: Context) {}
}
