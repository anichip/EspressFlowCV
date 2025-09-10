import SwiftUI

struct ResultView: View {
    let shot: EspressoShot
    let onDismiss: () -> Void
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Result Header
                    VStack(spacing: 16) {
                        // Result icon
                        Image(systemName: shot.isGoodShot ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                            .font(.system(size: 80))
                            .foregroundColor(shot.isGoodShot ? .green : .orange)
                        
                        // Result text
                        Text(shot.displayResult)
                            .font(.largeTitle)
                            .fontWeight(.bold)
                            .foregroundColor(shot.isGoodShot ? .green : .orange)
                        
                        // Confidence
                        if shot.confidence > 0 {
                            Text("Confidence: \(Int(shot.confidence * 100))%")
                                .font(.title3)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.top, 20)
                    
                    // Analysis Details
                    if let features = shot.features, !features.isEmpty {
                        AnalysisDetailsView(features: features, isGoodShot: shot.isGoodShot)
                    }
                    
                    // Recommendations
                    RecommendationsView(shot: shot)
                    
                    Spacer(minLength: 20)
                }
                .padding()
            }
            .navigationTitle("Analysis Result")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        onDismiss()
                        dismiss()
                    }
                    .fontWeight(.medium)
                }
            }
        }
    }
}

// MARK: - Analysis Details
struct AnalysisDetailsView: View {
    let features: [String: Double]
    let isGoodShot: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Analysis Details")
                .font(.title2)
                .fontWeight(.semibold)
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                ForEach(Array(features.keys.sorted()), id: \.self) { key in
                    FeatureCard(
                        name: formatFeatureName(key),
                        value: features[key] ?? 0,
                        unit: getFeatureUnit(key)
                    )
                }
            }
        }
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
    
    private func formatFeatureName(_ key: String) -> String {
        switch key {
        case "onset_time_s": return "Onset Time"
        case "continuity": return "Continuity"
        case "mean_width": return "Avg Width"
        case "cv_width": return "Width CV"
        case "amp_width": return "Width Range"
        case "slope_width": return "Width Slope"
        case "jitter_cx": return "Stability"
        case "delta_val": return "Brightness Δ"
        case "delta_hue": return "Color Δ"
        case "flicker": return "Flicker"
        default: return key.capitalized
        }
    }
    
    private func getFeatureUnit(_ key: String) -> String {
        switch key {
        case "onset_time_s": return "s"
        case "continuity": return "%"
        case "mean_width", "amp_width": return "px"
        case "cv_width": return ""
        case "slope_width": return "px/s"
        case "jitter_cx": return "px"
        case "delta_val", "delta_hue": return ""
        case "flicker": return "count"
        default: return ""
        }
    }
}

struct FeatureCard: View {
    let name: String
    let value: Double
    let unit: String
    
    var body: some View {
        VStack(spacing: 4) {
            Text(name)
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            HStack(alignment: .bottom, spacing: 2) {
                Text(formatValue(value))
                    .font(.title3)
                    .fontWeight(.medium)
                
                if !unit.isEmpty {
                    Text(unit)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(Color.white)
        .cornerRadius(8)
    }
    
    private func formatValue(_ value: Double) -> String {
        if value < 1 {
            return String(format: "%.3f", value)
        } else if value < 10 {
            return String(format: "%.2f", value)
        } else {
            return String(format: "%.1f", value)
        }
    }
}

// MARK: - Recommendations
struct RecommendationsView: View {
    let shot: EspressoShot
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Recommendations")
                .font(.title2)
                .fontWeight(.semibold)
            
            if shot.isGoodShot {
                GoodShotRecommendations()
            } else {
                UnderExtractedRecommendations()
            }
        }
        .padding()
        .background(shot.isGoodShot ? Color.green.opacity(0.1) : Color.orange.opacity(0.1))
        .cornerRadius(12)
    }
}

struct GoodShotRecommendations: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            RecommendationRow(
                icon: "checkmark.circle.fill",
                text: "Great extraction! Your technique is working well.",
                color: .green
            )
            
            RecommendationRow(
                icon: "arrow.clockwise",
                text: "Try to replicate these settings for consistency.",
                color: .green
            )
            
            RecommendationRow(
                icon: "note.text",
                text: "Note your grind size, dose, and timing for future reference.",
                color: .green
            )
        }
    }
}

struct UnderExtractedRecommendations: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            RecommendationRow(
                icon: "wrench.and.screwdriver",
                text: "Try a finer grind size to slow extraction.",
                color: .orange
            )
            
            RecommendationRow(
                icon: "thermometer",
                text: "Check water temperature (should be ~200°F).",
                color: .orange
            )
            
            RecommendationRow(
                icon: "timer",
                text: "Aim for 25-30 second extraction time.",
                color: .orange
            )
            
            RecommendationRow(
                icon: "scale.3d",
                text: "Ensure even tamping pressure (~30lbs).",
                color: .orange
            )
        }
    }
}

struct RecommendationRow: View {
    let icon: String
    let text: String
    let color: Color
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(color)
                .font(.body)
                .frame(width: 20)
            
            Text(text)
                .font(.subheadline)
        }
    }
}

#Preview {
    ResultView(
        shot: EspressoShot(
            id: 1,
            filename: "test.mp4",
            recordedAt: Date(),
            analysisResult: "good",
            confidence: 0.87,
            features: [
                "onset_time_s": 2.5,
                "continuity": 0.95,
                "mean_width": 25.3,
                "flicker": 2.0
            ],
            videoDurationS: 8.5,
            notes: ""
        )
    ) {
        // onDismiss
    }
}