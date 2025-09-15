import SwiftUI

struct AboutView: View {
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // App Icon and Title
                    VStack(spacing: 12) {
                        Image(systemName: "cup.and.saucer.fill")
                            .font(.system(size: 80))
                            .foregroundColor(.brown)
                        
                        Text("EspressFlowCV")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                        
                        Text("Version 1.0")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.top, 20)
                    
                    // Developer Info
                    InfoSection(title: "Developer") {
                        Text("Built with love for coding and coffee ☕")
                            .font(.body)
                            .multilineTextAlignment(.center)
                    }
                    
                    // How It Works
                    InfoSection(title: "How It Works") {
                        VStack(alignment: .leading, spacing: 12) {
                            FeatureRow(
                                icon: "video.circle",
                                title: "Records your espresso extraction",
                                description: "Capture the first 7 seconds of your shot"
                            )
                            
                            FeatureRow(
                                icon: "eye.circle",
                                title: "Analyzes flow characteristics",
                                description: "Computer vision examines stream properties"
                            )
                            
                            FeatureRow(
                                icon: "brain.head.profile",
                                title: "Provides instant feedback",
                                description: "Machine learning classifies extraction quality"
                            )
                            
                            FeatureRow(
                                icon: "chart.pie",
                                title: "Tracks your progress over time",
                                description: "Build a history of your espresso journey"
                            )
                        }
                    }
                    
                    // Technical Details
                    InfoSection(title: "Technology") {
                        VStack(alignment: .leading, spacing: 8) {
                            TechRow(label: "Computer Vision", value: "OpenCV")
                            TechRow(label: "Machine Learning", value: "Scikit-Learn")
                            TechRow(label: "Backend", value: "Flask API")
                            TechRow(label: "Database", value: "SQLite")
                            TechRow(label: "Frontend", value: "Swift")
                        }
                    }
                    
                    // Tips Section
//                    InfoSection(title: "Pro Tips") {
//                        VStack(alignment: .leading, spacing: 8) {
//                            TipRow("Use consistent lighting for best results")
//                            TipRow("Keep camera steady during recording")
//                            TipRow("Position cup directly under portafilter")
//                            TipRow("Record from a front-center angle")
//                            TipRow("Clean portafilter regularly for clear analysis")
//                        }
//                    }
                    
                    Spacer(minLength: 40)
                }
                .padding()
            }
            .navigationTitle("About")
        }
    }
}

// MARK: - Supporting Views
struct InfoSection<Content: View>: View {
    let title: String
    let content: Content
    
    init(title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.title2)
                .fontWeight(.semibold)
            
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
}

struct FeatureRow: View {
    let icon: String
    let title: String
    let description: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.brown)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .fontWeight(.medium)
                
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
    }
}

struct TechRow: View {
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            
            Spacer()
            
            Text(value)
                .fontWeight(.medium)
        }
    }
}

struct TipRow: View {
    let tip: String
    
    init(_ tip: String) {
        self.tip = tip
    }
    
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "lightbulb.fill")
                .font(.caption)
                .foregroundColor(.orange)
                .frame(width: 12)
            
            Text(tip)
                .font(.subheadline)
        }
    }
}

#Preview {
    AboutView()
}
