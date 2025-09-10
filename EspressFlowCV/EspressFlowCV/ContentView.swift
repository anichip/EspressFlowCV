import SwiftUI

struct ContentView: View {
    @StateObject private var appState = AppState()
    
    var body: some View {
        TabView {
            RecordingView()
                .tabItem {
                    Image(systemName: "video.circle")
                    Text("Record")
                }
                .environmentObject(appState)
            
            HistoryView()
                .tabItem {
                    Image(systemName: "chart.pie")
                    Text("History")
                }
                .environmentObject(appState)
            
            AboutView()
                .tabItem {
                    Image(systemName: "info.circle")
                    Text("About")
                }
                .environmentObject(appState)
        }
        .accentColor(.brown)
    }
}

#Preview {
    ContentView()
}