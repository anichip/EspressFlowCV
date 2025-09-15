# Next Session Priorities - EspressFlowCV

## 🏪 **APP STORE DEPLOYMENT PRIORITIES** (NEW)

### Critical Issues for App Store Submission

#### 2. **Hardcoded API URL** (CRITICAL)
- APIService.swift:4 has local IP address `"http://192.168.86.53:5000"`
- Won't work for production users
- Need to implement configurable endpoint or production server
- Consider environment-based configuration (dev/staging/prod)

#### 3. **iOS Deployment Target Too High** (MEDIUM PRIORITY)
- Currently set to iOS 18.5 (lines 325, 383 in project.pbxproj)
- Should be lowered to iOS 15/16 for broader device compatibility
- Will increase potential user base significantly

#### 4. **Bundle ID Setup** (REQUIRED)
- Current: `Ani.EspressFlowCV`
- Must match Apple Developer account team ID and app identifier
- Update in project.pbxproj lines 415, 445

#### 5. **App Store Metadata Missing** (REQUIRED)
- No app description, keywords, or category configured
- Need compelling app store description
- Define app category (likely Food & Drink or Utilities)
- Add relevant keywords for discoverability

#### 6. **Privacy Policy** (LIKELY REQUIRED)
- Camera/microphone permissions already have descriptions
- May need hosted privacy policy URL for App Store submission
- Required if app collects any user data or uses analytics

### Implementation Priority Order:
1. **Fix API URL configuration** - Critical for functionality
2. **Create app icons** - Required by Apple
3. **Lower deployment target** - Expand compatibility
4. **Configure bundle ID** - Match developer account
5. **Add App Store metadata** - Complete submission requirements
6. **Test on physical devices** - Ensure camera functionality works

## 🎯 High Priority Issues to Address

### 3. **Missing Instant Feedback**
- **Problem**: Result popup doesn't appear after analysis completes
- **Current workaround**: Users must check History tab to see results
- **Location**: RecordingView.swift - `showingResult` sheet not triggering
- **API works perfectly**: Analysis completes and returns to iOS app successfully

### 4. **Testing Setup**
- ✅ **Working**: USB cable connection allows testing on iPhone
- ✅ **Working**: API server and ML model functional
- ✅ **Working**: History tab displays completed analyses

## 🔧 Current Status

### ✅ **Working Components:**
- ML pipeline (video → features → classification)
- Flask API server with trained Random Forest model
- Database storage and retrieval
- iOS app history display
- USB debugging and testing

### ❌ **Broken Components:**
- Camera permission initialization
- Real-time result popup display
- Potentially ML accuracy for real-world conditions

## 📋 Next Session Action Plan

1. **Fix camera initialization bug** in RecordingView.swift
2. **Debug result sheet display** issue (showingResult not triggering)
3. **Collect more training data** for model improvement
4. **Test real-world accuracy** with various espresso setups
5. **Consider model retraining** if accuracy issues persist

## 💾 **Current System State:**
- API Server: Shut down (restart with `python api_server.py`)
- Model Files: Saved (`espresso_model.joblib`, `model_metadata.joblib`)
- Database: Intact with test shots (`espresso_shots.db`)
- iOS App: Latest code compiled and working via USB

---
*Session completed: 2025-09-13*
*Next session: Focus on camera + instant feedback + ML accuracy*