import SwiftUI
import Charts

struct HistoryView: View {
    @EnvironmentObject var appState: AppState
    @State private var showingDeleteAlert = false
    @State private var shotToDelete: EspressoShot?
    @Environment(\.scenePhase) private var scenePhase
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Progress Section
                    if let summary = appState.summary {
                        ProgressSectionView(summary: summary)
                    }
                    
                    // Recent Shots Section
                    RecentShotsSection()
                }
                .padding()
            }
            .navigationTitle("Pull History")
            .refreshable {
                await appState.refreshShots()
                await appState.refreshSummary()
            }
            .onChange(of: scenePhase) { newPhase in
                if newPhase == .active {
                    // Refresh data when app becomes active (e.g., from background)
                    Task {
                        await appState.refreshShots()
                        await appState.refreshSummary()
                    }
                }
            }
        }
        .alert("Delete Shot", isPresented: $showingDeleteAlert) {
            Button("Cancel", role: .cancel) { }
            Button("Delete", role: .destructive) {
                if let shot = shotToDelete {
                    Task {
                        await appState.deleteShot(shot)
                    }
                }
            }
        } message: {
            Text("Are you sure you want to delete this shot? This action cannot be undone.")
        }
    }
    
    @ViewBuilder
    private func RecentShotsSection() -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Recent Shots")
                    .font(.title2)
                    .fontWeight(.semibold)
                
                Spacer()
                
                if appState.isLoading {
                    ProgressView()
                        .scaleEffect(0.8)
                }
            }
            
            if appState.shots.isEmpty {
                if appState.isLoading || appState.isRetrying {
                    VStack(spacing: 12) {
                        ProgressView()
                        if appState.isRetrying {
                            Text(appState.errorMessage ?? "Retrying connection...")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        } else {
                            Text("Loading shots...")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding()
                } else if appState.errorMessage != nil {
                    ErrorStateView(
                        message: appState.errorMessage!,
                        onRetry: {
                            Task {
                                await appState.retryConnection()
                            }
                        }
                    )
                } else {
                    EmptyStateView()
                }
            } else {
                LazyVStack(spacing: 12) {
                    ForEach(appState.shots) { shot in
                        ShotRowView(shot: shot) {
                            shotToDelete = shot
                            showingDeleteAlert = true
                        }
                    }
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - Progress Section
struct ProgressSectionView: View {
    let summary: ShotsSummary
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Your Progress")
                .font(.title2)
                .fontWeight(.semibold)
            
            HStack(spacing: 20) {
                // Pie Chart
                PieChartView(summary: summary)
                    .frame(width: 120, height: 120)
                
                // Statistics
                VStack(alignment: .leading, spacing: 8) {
                    StatRow(label: "Total Shots", value: "\(summary.totalShots)")
                    StatRow(label: "Great Pulls", value: "\(summary.goodShots) (\(Int(summary.goodPercentage))%)", color: .green)
                    StatRow(label: "Under Extracted", value: "\(summary.underShots) (\(Int(summary.underPercentage))%)", color: .orange)
                }
                
                Spacer()
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - Pie Chart
struct PieChartView: View {
    let summary: ShotsSummary
    
    var body: some View {
        ZStack {
            // Good shots
            Circle()
                .trim(from: 0, to: summary.goodPercentage / 100.0)
                .stroke(Color.green, lineWidth: 20)
                .rotationEffect(.degrees(-90))
            
            // Under shots
            Circle()
                .trim(from: summary.goodPercentage / 100.0, to: 1.0)
                .stroke(Color.orange, lineWidth: 20)
                .rotationEffect(.degrees(-90))
            
            // Center text
            VStack {
                Text("\(summary.totalShots)")
                    .font(.title2)
                    .fontWeight(.bold)
                Text("shots")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
    }
}

// MARK: - Stat Row
struct StatRow: View {
    let label: String
    let value: String
    let color: Color?
    
    init(label: String, value: String, color: Color? = nil) {
        self.label = label
        self.value = value
        self.color = color
    }
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
                .foregroundColor(color ?? .primary)
        }
    }
}

// MARK: - Shot Row
struct ShotRowView: View {
    let shot: EspressoShot
    let onDelete: () -> Void
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Image(systemName: shot.isGoodShot ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                        .foregroundColor(shot.isGoodShot ? .green : .orange)
                    
                    Text(shot.displayResult)
                        .fontWeight(.medium)
                }
                
                Text(shot.recordedAt, style: .date)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if shot.confidence > 0 {
                    Text("Confidence: \(Int(shot.confidence * 100))%")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            
            Spacer()
            
            Button(action: onDelete) {
                Image(systemName: "trash")
                    .foregroundColor(.red)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(8)
        .shadow(color: Color.primary.opacity(0.1), radius: 1)
    }
}

// MARK: - Error State
struct ErrorStateView: View {
    let message: String
    let onRetry: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.exclamationmark")
                .font(.system(size: 50))
                .foregroundColor(.orange)

            Text("Connection Error")
                .font(.title3)
                .fontWeight(.medium)

            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Button(action: onRetry) {
                HStack {
                    Image(systemName: "arrow.clockwise")
                    Text("Retry Connection")
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
        }
        .padding(40)
    }
}

// MARK: - Empty State
struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "cup.and.saucer")
                .font(.system(size: 60))
                .foregroundColor(.brown.opacity(0.5))

            Text("No shots yet")
                .font(.title3)
                .fontWeight(.medium)

            Text("Record your first espresso shot to see your progress here!")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }
}

#Preview {
    HistoryView()
        .environmentObject(AppState())
}
