import SwiftUI

struct TipsView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "lightbulb.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.orange)
                        
                        Text("Recording Guide")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                    }
                    .padding(.top)
                    
                    // Camera Position Section
                    TipSection(
                        title: "📐 Camera Position",
                        icon: "camera.fill",
                        color: .blue
                    ) {
                        VStack(alignment: .leading, spacing: 12) {
                            TipPoint("Flat front angle")
                            TipPoint("Portafilter at top of frame")
                            TipPoint("Cup at bottom of frame")
                            TipPoint("Maximum distance between them")
                            
                            HStack(spacing: 20) {
                                // Good example
                                VStack {
                                    Text("DO ✅")
                                        .font(.caption)
                                        .fontWeight(.bold)
                                        .foregroundColor(.green)
                                    
                                    Rectangle()
                                        .fill(Color.green.opacity(0.2))
                                        .frame(height: 80)
                                        .overlay(
                                            VStack(spacing: 4) {
                                                Text("🔧 Portafilter")
                                                    .font(.caption2)
                                                Text("☕ Stream")
                                                    .font(.caption2)
                                                Text("☕ Cup")
                                                    .font(.caption2)
                                            }
                                        )
                                        .cornerRadius(8)
                                    
                                    Text("Centered")
                                        .font(.caption2)
                                        .foregroundColor(.green)
                                }
                                
                                // Bad example
                                VStack {
                                    Text("DON'T ❌")
                                        .font(.caption)
                                        .fontWeight(.bold)
                                        .foregroundColor(.red)
                                    
                                    Rectangle()
                                        .fill(Color.red.opacity(0.2))
                                        .frame(height: 80)
                                        .overlay(
                                            Text("🔧\n   ☕\n     ☕")
                                                .font(.caption2)
                                                .multilineTextAlignment(.leading)
                                        )
                                        .cornerRadius(8)
                                    
                                    Text("Angled view")
                                        .font(.caption2)
                                        .foregroundColor(.red)
                                }
                            }
                        }
                    }
                    
                    // Recording Tips Section
                    TipSection(
                        title: "🎯 Recording Tips",
                        icon: "record.circle",
                        color: .red
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            TipPoint("Use tripod or steady surface for stability")
                            TipPoint("Start recording just before first drip")
                            TipPoint("Stand in front to block reflections")
                            TipPoint("Wipe chrome surfaces beforehand")
                            TipPoint("Ensure good lighting (avoid shadows)")
                            TipPoint("Record for at least 8 seconds")
                        }
                    }
                    
                    // Barista Tips Section
                    TipSection(
                        title: "☕ Barista Tips",
                        icon: "cup.and.saucer.fill",
                        color: .brown
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            TipPoint("Adjust grind size for flow rate")
                            TipPoint("Heat portafilter before dosing")
                            TipPoint("Tamp evenly for consistent bed")
                            TipPoint("Dial in your brew ratio (1:2 typical)")
                            TipPoint("Check water temperature (200°F)")
                            TipPoint("Use fresh, quality beans")
                            TipPoint("Pre-infuse for 2-3 seconds")
                        }
                    }
                    
                    // Analysis Info Section
                    TipSection(
                        title: "🧠 What We Analyze",
                        icon: "brain.head.profile",
                        color: .purple
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            TipPoint("Stream onset timing")
                            TipPoint("Flow consistency and continuity")
                            TipPoint("Stream width and stability")
                            TipPoint("Color evolution during extraction")
                            TipPoint("Flow interruptions and flicker")
                            TipPoint("Overall extraction dynamics")
                        }
                    }
                    
                    Spacer(minLength: 20)
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Got It!") {
                        dismiss()
                    }
                    .fontWeight(.medium)
                }
            }
        }
    }
}

// MARK: - Supporting Views
struct TipSection<Content: View>: View {
    let title: String
    let icon: String
    let color: Color
    let content: Content
    
    init(title: String, icon: String, color: Color, @ViewBuilder content: () -> Content) {
        self.title = title
        self.icon = icon
        self.color = color
        self.content = content()
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                    .font(.title2)
                
                Text(title)
                    .font(.title2)
                    .fontWeight(.semibold)
            }
            
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(color.opacity(0.1))
        .cornerRadius(12)
    }
}

struct TipPoint: View {
    let text: String
    
    init(_ text: String) {
        self.text = text
    }
    
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text("•")
                .fontWeight(.bold)
                .foregroundColor(.secondary)
            
            Text(text)
                .font(.subheadline)
        }
    }
}

#Preview {
    TipsView()
}