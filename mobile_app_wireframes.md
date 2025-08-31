# EspressFlowCV Mobile App Wireframes

**Created:** December 2024  
**Purpose:** Text-based wireframes for single-user espresso analysis mobile app  
**Platform:** React Native (iOS + Android)

## App Specifications

- **Name:** EspressFlowCV
- **Core Function:** Record espresso extraction → Analyze first 8 seconds → Classify as "Great Pull!" or "Slightly Under"
- **Storage:** Local only (no user accounts, SQLite + video files)
- **Analysis:** Uses existing espresso_flow_features.py pipeline (10 features extracted from 7-second flow analysis)

## Three-Page Structure

### 📱 **Page 1: Recording (Main Page)**
```
╔════════════════════════════════════════╗
║                EspressFlowCV           ║
╠════════════════════════════════════════╣
║                                        ║
║ ┌─ Camera Preview ──────────────────┐   ║
║ │                                  │   ║
║ │     ┌─ Alignment Guide ─────┐     │   ║
║ │     │    [Portafilter]     │     │   ║
║ │     │         │            │     │   ║
║ │     │      Flow Zone       │     │   ║
║ │     │         │            │     │   ║
║ │     │      [Cup Here]      │     │   ║
║ │     └──────────────────────┘     │   ║
║ │                                  │   ║
║ └──────────────────────────────────┘   ║
║                                        ║
║ Record when you're ready champ! 🎬     ║
║ [●●●●●○○○] Recording: 5.2s             ║
║                                        ║
║ ┌──[ RECORD ]──┐ ┌─[ 💡 Tips ]───┐     ║
║ │   ● START    │ │  Quick Guide  │     ║
║ └──────────────┘ └───────────────┘     ║
║                                        ║
║ [🎥Record] [📊History] [ℹ️ About]       ║
╚════════════════════════════════════════╝
```

**Key Features:**
- Live camera preview with alignment overlay
- Encouraging message: "Record when you're ready champ!"
- Recording progress indicator
- Two buttons: RECORD and Quick Tips
- Bottom navigation consistent across all pages

### 📱 **Page 2: History**
```
╔════════════════════════════════════════╗
║              Shot History              ║
╠════════════════════════════════════════╣
║                                        ║
║ ┌─ Your Progress ─────────────────────┐ ║
║ │     🥧 Pie Chart                   │ ║
║ │   Great: 67% (18 shots)            │ ║
║ │   Under: 33% (9 shots)             │ ║
║ │   Total: 27 shots analyzed         │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║ ┌─ Recent Shots ──────────────────────┐ ║
║ │ Dec 3, 2024 • 2:15 PM             │ ║
║ │ ✅ Great Pull!              [🗑️]   │ ║
║ │                                    │ ║
║ │ Dec 3, 2024 • 9:30 AM             │ ║
║ │ ⚠️ Slightly Under               [🗑️]   │ ║
║ │                                    │ ║
║ │ Dec 2, 2024 • 4:45 PM             │ ║
║ │ ✅ Great Pull!              [🗑️]   │ ║
║ │                                    │ ║
║ │ ↓ Scroll for more...              │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║ [🎥Record] [📊History] [ℹ️ About]       ║
╚════════════════════════════════════════╝
```

**Key Features:**
- Pie chart showing lifetime Good vs Under-extracted percentages
- Scrollable list of all shots with timestamps
- Individual delete buttons for each shot
- Friendly result messages: "Great Pull!" vs "Slightly Under"

### 📱 **Page 3: About/Credits**
```
╔════════════════════════════════════════╗
║                About                   ║
╠════════════════════════════════════════╣
║                                        ║
║ ┌─ EspressFlowCV ─────────────────────┐ ║
║ │ Version 1.0                        │ ║
║ │                                    │ ║
║ │ Developed by [Your Name]           │ ║
║ │                                    │ ║
║ │ Using computer vision and machine  │ ║
║ │ learning to analyze espresso       │ ║
║ │ extraction quality in real-time.   │ ║
║ │                                    │ ║
║ │ Built with love for coffee ☕      │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║ ┌─ How It Works ──────────────────────┐ ║
║ │ • Records your espresso extraction │ ║
║ │ • Analyzes flow characteristics    │ ║
║ │ • Provides instant feedback       │ ║
║ │ • Tracks your progress over time   │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║ [🎥Record] [📊History] [ℹ️ About]       ║
╚════════════════════════════════════════╝
```

**Key Features:**
- App info and developer credits
- Simple explanation of functionality
- Room to expand with more details as development progresses

## Modal: Recording Guide

### 📱 **Quick Tips Modal (Scrollable)**
```
╔════════════════════════════════════════╗
║            Recording Guide             ║
╠════════════════════════════════════════╣
║                                        ║
║ 📐 Camera Position:                    ║
║ • Flat front angle                     ║
║ • Portafilter at top                   ║
║ • Cup at bottom                        ║
║ • Max distance between them            ║
║                                        ║
║ ┌─ DO ✅ ──────┐ ┌─ DON'T ❌ ─────┐    ║
║ │ [Good Pic]  │ │ [Bad Pic]     │    ║
║ │ Centered    │ │ Angled view   │    ║
║ └─────────────┘ └───────────────┘    ║
║                                        ║
║ 🎯 Recording Tips:                     ║
║ • Use tripod for stability            ║
║ • Start just before first drip        ║
║ • Stand in front to block reflections ║
║ • Wipe chrome surfaces beforehand     ║
║                                        ║
║ ↓ Scroll for more tips...              ║
║ ═══════════════════════════════════════ ║
║                                        ║
║ ☕ Barista Tips:                       ║
║ • Adjust grind size for flow rate     ║
║ • Heat portafilter before dosing      ║
║ • Tamp evenly for consistent bed      ║
║ • Dial in your brew ratio            ║
║ • Check water temperature (200°F)     ║
║ • Use fresh, quality beans            ║
║                                        ║
║              [Got It!]                 ║
╚════════════════════════════════════════╝
```

**Key Features:**
- Comprehensive recording guidance based on computer vision requirements
- Visual examples of good vs bad camera positioning
- Scrollable content with both technical recording tips AND barista advice
- Practical tips to improve extraction quality

## User Experience Flow

### Recording Process
1. **User opens app** → Lands on Recording page
2. **User taps "Tips"** → Views guidance modal, closes with "Got It!"
3. **User positions camera** → Alignment guides help with framing
4. **User taps "RECORD"** → App records full extraction (any length)
5. **App processes video** → Analyzes first 8 seconds (skipping first 1 second)
6. **App shows result** → "Great Pull!" or "Slightly Under" + tips
7. **Result saved** → Automatically added to History page

### Data Storage
```javascript
// SQLite Schema
shots: {
  id: INTEGER,
  filename: TEXT,        // "shot_20241203_142301.mp4" 
  date: TEXT,           // "2024-12-03"
  result: TEXT,         // "good" | "under"
  confidence: REAL      // 0.0 - 1.0 (future feature)
}
```

## Technical Integration Points

### Processing Pipeline
```
User Video → Frame Extraction → espresso_flow_features.py → ML Model → Result
    │              │                        │                   │
    │              │                        │                   └─ Store in SQLite
    │              │                        └─ 10 features extracted
    │              └─ First 8 seconds, skip second 1, analyze seconds 2-8  
    └─ Full length recording (user flexibility)
```

### Development Phases
- **Phase 1:** UI Design + Camera Setup (current)
- **Phase 2:** Processing Bridge + ML Integration  
- **Phase 3:** Polish + App Store Preparation

## Design Notes

### Tone & Language
- **Encouraging:** "Record when you're ready champ!"
- **Friendly results:** "Great Pull!" vs "Slightly Under"
- **Helpful:** Detailed tips for both recording technique and barista skills
- **Non-intimidating:** No technical jargon in user-facing text

### Visual Hierarchy
- **Camera preview** takes center stage on main page
- **Progress charts** prominently displayed on history page
- **Tips are accessible** but don't clutter the main interface
- **Navigation is consistent** across all three pages

This wireframe serves as the blueprint for EspressFlowCV development, balancing technical computer vision requirements with user-friendly espresso analysis experience.