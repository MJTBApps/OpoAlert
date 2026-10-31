import Foundation

/// El PDF oficial se ve dentro de la app (como `PdfViewerActivity.kt`).
public enum OfficialDocument {
    /// Enlaces que son páginas web (fichas) y no PDF: se abren en el navegador.
    public static func isPdf(_ notice: Notice) -> Bool {
        !(notice.id.hasPrefix("CIDO") ||
            notice.province == "Teruel" ||
            notice.url.contains("ExportarBoletinServlet") ||
            notice.url.contains("dogc.gencat.cat/") ||
            notice.url.contains("bon.navarra.es/"))
    }

    /// «…/boletin.pdf#page=29»: página en la que empieza el anuncio (1 si no la indica).
    public static func startPage(_ url: String) -> Int {
        guard let match = Patterns.matches(#"#page=(\d{1,4})$"#, url).first, let page = Int(match[1]) else { return 1 }
        return max(page, 1)
    }

    public static func looksLikePdf(_ data: Data) -> Bool {
        data.prefix(5).elementsEqual("%PDF-".utf8)
    }
}
