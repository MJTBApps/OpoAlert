import OpoAlertCore
import SwiftUI

/// Colores de la app Android, para que las dos se vean igual.
enum Palette {
    static let blue = Color(hex: 0x1E4FD5)
    static let navy = Color(hex: 0x17243C)
    static let slate = Color(hex: 0x64748B)
    static let background = Color(hex: 0xF6F8FC)
    static let poolText = Color(hex: 0x0F766E)
    static let poolFill = Color(hex: 0xD9F5EB)
    static let positionFill = Color(hex: 0xE4EDFF)
    static let procedureText = Color(hex: 0xA16207)
    static let procedureFill = Color(hex: 0xFEF3C7)
    static let star = Color(hex: 0xB7791F)
    static let favoriteBorder = Color(hex: 0xEEC77A)
    static let border = Color(hex: 0xDEE5EF)
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255)
    }
}

/// Tres pestañas, como en Android: Explorar, Favoritas y Alertas.
struct RootView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        TabView(selection: $model.tab) {
            NavigationStack { NoticeListView(mode: .explore) }
                .tabItem { Label("Explorar", systemImage: "doc.text.magnifyingglass") }
                .tag(AppTab.explore)
            NavigationStack { NoticeListView(mode: .favorites) }
                .tabItem { Label("Favoritas", systemImage: "star") }
                .tag(AppTab.favorites)
            NavigationStack { AlertsView() }
                .tabItem { Label("Alertas", systemImage: "bell") }
                .tag(AppTab.alerts)
        }
        .sheet(isPresented: $model.showSourcePicker) {
            SourcePickerView(firstLaunch: !model.store.pickerShown)
        }
        .sheet(item: $model.openedNotice) { notice in
            NavigationStack {
                NoticeDetailView(notice: notice)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cerrar") { model.openedNotice = nil }
                        }
                    }
            }
        }
    }
}
