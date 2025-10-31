# LaborLooker Mobile App Development
# React Native & Flutter Setup for iOS and Android

This directory contains the mobile app foundations for LaborLooker, designed to work with Google Play Store and iOS App Store deployment.

## 📱 Mobile App Architecture

### API Integration
- **Base URL**: `https://your-domain.com/api/v1`
- **Authentication**: Bearer token system
- **Response Format**: JSON
- **Rate Limiting**: Built-in protection

### Supported Platforms
- **iOS**: React Native & Flutter
- **Android**: React Native & Flutter
- **Web**: Progressive Web App (PWA) capability

## 🚀 Available API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/users/profile` - Get user profile

### Ratings & Reviews
- `GET /api/v1/ratings/{user_id}` - Get user ratings
- `POST /api/v1/ratings` - Submit new rating

### Contractor Search
- `POST /api/v1/contractors/search` - Search contractors

### Health Check
- `GET /api/v1/health` - API status

## 📁 Directory Structure

```
mobile-app/
├── react-native/          # React Native app
│   ├── package.json       # Dependencies
│   ├── app.json          # App configuration
│   └── README.md         # React Native setup
├── flutter/              # Flutter app
│   ├── pubspec.yaml      # Dependencies
│   ├── android/          # Android configuration
│   ├── ios/              # iOS configuration
│   └── README.md         # Flutter setup
└── shared/               # Shared assets and configs
    ├── api/              # API client libraries
    ├── assets/           # Images, fonts, etc.
    └── configs/          # App store configurations
```

## 🛠 Development Setup

### Prerequisites
- Node.js 18+ (for React Native)
- Flutter SDK 3.0+ (for Flutter)
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)

### React Native Setup
```bash
cd mobile-app/react-native
npm install
npx react-native run-android  # For Android
npx react-native run-ios      # For iOS (macOS only)
```

### Flutter Setup
```bash
cd mobile-app/flutter
flutter pub get
flutter run android          # For Android
flutter run ios              # For iOS (macOS only)
```

## 🏪 App Store Deployment

### Google Play Store (Android)
1. Configure `android/app/build.gradle`
2. Generate signed APK: `cd android && ./gradlew assembleRelease`
3. Upload to Google Play Console

### iOS App Store
1. Configure `ios/Runner.xcworkspace` in Xcode
2. Archive and upload to App Store Connect
3. Submit for review

## 🔐 Security Features

- **Token-based authentication**
- **SSL/TLS encryption**
- **Rate limiting protection**
- **Input validation**
- **Secure storage for tokens**

## 📊 Analytics & Monitoring

- **Google Analytics** integration ready
- **Crashlytics** for error reporting
- **Performance monitoring**
- **User behavior tracking**

## 🎨 Design System

- **Material Design** (Android)
- **Human Interface Guidelines** (iOS)
- **Consistent branding** across platforms
- **Accessibility support**

---

## 🚀 Quick Start

1. **API First**: Test API endpoints with Postman/Insomnia
2. **Choose Platform**: React Native for faster development, Flutter for native performance
3. **Setup Environment**: Install platform-specific tools
4. **Development**: Start with authentication and basic navigation
5. **Testing**: Test on real devices before store submission

Your LaborLooker web application is **already mobile-ready** with full API support!