import SwiftUI

struct TipsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var expandedSections: Set<String> = []
    
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
                    CollapsibleTipSection(
                        title: "Camera Position",
                        icon: "camera.fill",
                        color: .blue,
                        isExpanded: expandedSections.contains("camera"),
                        onToggle: { toggleSection("camera") }
                    ) {
                        VStack(alignment: .leading, spacing: 7) {
                            TipPoint("Upright front angle")
//                            TipPoint("Portafilter spout at top of frame")
//                            TipPoint("Cup at bottom of frame")
                            TipPoint("Position cup directly under portafilter")
                            TipPoint("Maximize distance between portafilter spout and cup rim")
                            TipPoint("Capture as much stream in the middle as you can")
                            
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
                                                Text("🟤 Stream")
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
                    CollapsibleTipSection(
                        title: "Recording Tips",
                        icon: "record.circle",
                        color: .red,
                        isExpanded: expandedSections.contains("recording"),
                        onToggle: { toggleSection("recording") }
                    ) {
                        VStack(alignment: .leading, spacing: 7) {
                            TipPoint("Use tripod for stability")
                            TipPoint("Start recording just before first flow")
                            TipPoint("Stop recording after stream tapers off")
                            TipPoint("Stand behind camera to block reflections")
                            TipPoint("Wipe chrome surfaces beforehand")
                            TipPoint("Ensure good lighting (avoid shadows)")
                            TipPoint("Record for 10 seconds minimum")
                        }
                    }
                    
                    // Barista Tips Section
                    CollapsibleTipSection(
                        title: "Barista Tips",
                        icon: "cup.and.saucer.fill",
                        color: .brown,
                        isExpanded: expandedSections.contains("barista"),
                        onToggle: { toggleSection("barista") }
                    ) {
                        VStack(alignment: .leading, spacing: 7) {
                            TipPoint("Slow drip? (Overextracted) grind coarser")
                            TipPoint("Fast sandy blob? (Underextracted) grind finer")
                            TipPoint("Heat portafilter before pulling")
                            TipPoint("Tamp evenly for consistent bed")
                            TipPoint("Dial in your brew ratio (1:2 typical)")
                            TipPoint("Check water temperature (200°F)")
                        }
                    }
                    
                    // Analysis Info Section
//                    TipSection(
//                        title: "What We Analyze",
//                        icon: "brain.head.profile",
//                        color: .purple
//                    ) {
//                        VStack(alignment: .leading, spacing: 8) {
//                            TipPoint("Stream onset timing")
//                            TipPoint("Flow consistency and continuity")
//                            TipPoint("Stream width and stability")
//                            TipPoint("Color evolution during extraction")
//                            TipPoint("Flow interruptions and flicker")
//                            TipPoint("Overall extraction dynamics")
//                        }
//                    }
                    
                    Spacer(minLength: 20)
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Back") {
                        dismiss()
                    }
                    .fontWeight(.medium)
                    .font(.title2)
                }
            }
        }
    }
    
    private func toggleSection(_ sectionId: String) {
        withAnimation(.easeInOut(duration: 0.3)) {
            if expandedSections.contains(sectionId) {
                expandedSections.remove(sectionId)
            } else {
                expandedSections.insert(sectionId)
            }
        }
    }
}

// MARK: - Supporting Views
struct CollapsibleTipSection<Content: View>: View {
    let title: String
    let icon: String
    let color: Color
    let isExpanded: Bool
    let onToggle: () -> Void
    let content: Content
    
    init(title: String, icon: String, color: Color, isExpanded: Bool, onToggle: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.title = title
        self.icon = icon
        self.color = color
        self.isExpanded = isExpanded
        self.onToggle = onToggle
        self.content = content()
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header (always visible, tappable)
            Button(action: onToggle) {
                HStack {
                    Image(systemName: icon)
                        .foregroundColor(color)
                        .font(.title2)
                    
                    Text(title)
                        .font(.title2)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                    
                    Spacer()
                    
                    Image(systemName: "chevron.down")
                        .foregroundColor(.secondary)
                        .font(.subheadline)
                        .rotationEffect(.degrees(isExpanded ? 180 : 0))
                }
                .padding()
                .background(color.opacity(0.1))
                .cornerRadius(12)
            }
            .buttonStyle(PlainButtonStyle())
            
            // Content (expandable)
            if isExpanded {
                VStack(alignment: .leading, spacing: 16) {
                    content
                }
                .padding()
                .background(color.opacity(0.05))
                .cornerRadius(12)
                .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

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
