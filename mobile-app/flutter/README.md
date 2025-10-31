# Flutter Mobile App - Build Instructions

## Prerequisites

1. **Flutter SDK**: Install Flutter SDK (3.10+ required)
   - Download from: https://flutter.dev/docs/get-started/install
   - Add Flutter to your PATH

2. **Development Tools**:
   - Android Studio or VS Code with Flutter extensions
   - Xcode (for iOS development on Mac)
   - Android SDK and emulators

3. **Dependencies**:
   ```bash
   flutter doctor
   ```

## Setup Instructions

1. **Navigate to Flutter app directory**:
   ```bash
   cd mobile-app/flutter
   ```

2. **Install dependencies**:
   ```bash
   flutter pub get
   ```

3. **Update API endpoint** in `lib/core/services/api_service.dart`:
   ```dart
   static const String baseUrl = 'https://your-domain.com/api/v1';
   ```

4. **Run the app**:
   ```bash
   # For development (debug mode)
   flutter run

   # For Android
   flutter run -d android

   # For iOS 
   flutter run -d ios

   # For web
   flutter run -d chrome
   ```

## Build for Production

### Android APK
```bash
flutter build apk --release
```

### Android App Bundle (for Play Store)
```bash
flutter build appbundle --release
```

### iOS (requires Mac)
```bash
flutter build ios --release
```

## Project Structure

```
lib/
├── core/
│   ├── models/          # Data models
│   ├── providers/       # Riverpod state providers
│   ├── services/        # API and utility services
│   └── theme/          # App theming
├── features/
│   ├── auth/           # Authentication screens
│   └── dashboard/      # Main app screens
├── app.dart            # App configuration and routing
└── main.dart           # Entry point
```

## Key Features

- **Authentication**: Login/Register with JWT tokens
- **Dashboard**: Overview of work requests and activity
- **Work Requests**: Create, view, and manage work requests
- **User Profiles**: Manage contractor/customer profiles
- **Responsive UI**: Material Design 3 with light/dark themes
- **State Management**: Riverpod for reactive state management
- **Navigation**: Go Router for declarative routing

## Configuration

### Environment Variables
Create appropriate configuration for different environments:

- Development: Local API endpoints
- Staging: Staging server endpoints  
- Production: Production server endpoints

### API Integration
The app connects to the Flask backend via REST API endpoints defined in `mobile_api_v2.py`.

## Testing

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage
```

## Troubleshooting

1. **Dependencies issues**: Run `flutter clean && flutter pub get`
2. **Build failures**: Check `flutter doctor` for missing dependencies
3. **API connection**: Verify backend server is running and accessible
4. **Authentication**: Ensure JWT tokens are properly stored and transmitted

## Next Steps

1. Add more feature screens (search, messaging, profile editing)
2. Implement push notifications
3. Add offline capabilities
4. Integrate camera/file upload features
5. Add payment integration
6. Implement real-time messaging