# LaborLooker Mobile App - React Native

A professional networking mobile application for contractors and customers to connect and manage work requests.

## 🚀 Features

### For Customers
- **Create Work Requests**: Post detailed job requirements with photos
- **Find Contractors**: Search for verified contractors by service type and location
- **Track Progress**: Monitor work request status and communicate with contractors
- **Secure Payments**: Handle invoicing and payments through the app
- **Review System**: Rate and review contractors after job completion

### For Contractors
- **Job Marketplace**: Browse available work requests in your area
- **Profile Management**: Showcase your skills, licenses, and portfolio
- **Bid Management**: Submit quotes and manage job proposals
- **Invoice Generation**: Create and send professional invoices
- **Schedule Management**: Track your jobs and appointments

### Shared Features
- **Real-time Notifications**: Stay updated on job status changes
- **Secure Authentication**: JWT-based authentication with 2FA support
- **Document Management**: Upload and share photos, contracts, and documents
- **Location Services**: GPS-based contractor search and job matching
- **Offline Support**: Basic functionality works without internet connection

## 📱 Technology Stack

- **Framework**: React Native 0.72.4
- **Navigation**: React Navigation 6
- **UI Components**: React Native Paper (Material Design)
- **State Management**: React Context API with useReducer
- **API Client**: Axios
- **Storage**: AsyncStorage
- **Maps**: React Native Maps
- **Camera**: React Native Image Picker
- **Authentication**: JWT tokens
- **Push Notifications**: Expo Notifications

## 🛠️ Installation

### Prerequisites
- Node.js 16.x or higher
- npm or yarn
- React Native CLI
- Android Studio (for Android development)
- Xcode (for iOS development)

### Setup Instructions

1. **Clone the repository**
   ```bash
   cd mobile-app/react-native
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Install iOS dependencies** (iOS only)
   ```bash
   cd ios && pod install && cd ..
   ```

4. **Configure environment**
   - Update API base URL in `src/services/api.js`
   - Add your Google Maps API key for location services
   - Configure push notification credentials

5. **Run the application**
   
   For Android:
   ```bash
   npm run android
   # or
   yarn android
   ```

   For iOS:
   ```bash
   npm run ios
   # or
   yarn ios
   ```

## 🏗️ Project Structure

```
src/
├── components/           # Reusable UI components
├── contexts/            # React Context providers
│   ├── AuthContext.js   # Authentication state
│   └── AppContext.js    # Application state
├── hooks/               # Custom React hooks
├── navigation/          # Navigation configuration
│   ├── AuthNavigator.js # Auth flow navigation
│   └── MainNavigator.js # Main app navigation
├── screens/             # Screen components
│   ├── auth/           # Authentication screens
│   ├── dashboard/      # Dashboard screens
│   ├── workRequests/   # Work request management
│   ├── contractors/    # Contractor search and profiles
│   ├── invoices/       # Billing and invoices
│   └── profile/        # User profile management
├── services/           # API and external services
│   └── api.js         # API client configuration
├── theme/              # App theme and styling
└── utils/              # Utility functions
```

## 🔐 Authentication Flow

1. **Welcome Screen**: Introduction and account type selection
2. **Registration**: Email, password, and account type (customer/contractor)
3. **Email Verification**: Users must verify email before login
4. **Login**: Email/password authentication with JWT tokens
5. **Two-Factor Authentication**: Optional 2FA for enhanced security
6. **Profile Setup**: Complete profile information after first login

## 📊 State Management

The app uses React Context API for state management:

- **AuthContext**: User authentication, login/logout, token management
- **AppContext**: Application data, work requests, profiles, invoices

## 🌐 API Integration

The mobile app communicates with the Flask backend through REST API endpoints:

- `POST /api/v1/auth/login` - User authentication
- `GET /api/v1/users/profile` - User profile data
- `GET /api/v1/work-requests` - Work request list
- `POST /api/v1/contractors/search` - Contractor search
- `GET /api/v1/invoices` - Invoice management

## 🔧 Configuration

### Environment Variables
Update the following configurations:

1. **API Base URL** (`src/services/api.js`):
   ```javascript
   const API_BASE_URL = 'https://your-domain.com/api/v1';
   ```

2. **Push Notifications**: Configure in `app.json`
3. **Maps API**: Add Google Maps API key
4. **Deep Linking**: Configure URL schemes for app linking

### App Configuration
- **Theme**: Customize colors and fonts in `src/theme/theme.js`
- **Navigation**: Modify tab structure in `src/navigation/MainNavigator.js`
- **Permissions**: Update required permissions in `app.json`

## 📱 Platform-Specific Features

### iOS
- Touch ID/Face ID authentication
- iOS-style navigation patterns
- Apple Pay integration (future feature)
- Core Location for GPS services

### Android
- Fingerprint authentication
- Material Design components
- Google Pay integration (future feature)
- Android location services

## 🧪 Testing

```bash
# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Run linting
npm run lint

# Type checking (if using TypeScript)
npm run type-check
```

## 📦 Building for Production

### Android Release Build
```bash
cd android
./gradlew assembleRelease
```

### iOS Release Build
```bash
npx react-native run-ios --configuration Release
```

### App Store Deployment
1. Update version numbers in `package.json` and platform configs
2. Build signed release APK/IPA
3. Upload to Google Play Store / Apple App Store
4. Fill out store listing with screenshots and descriptions

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Biometric Authentication**: Touch ID/Face ID support
- **SSL/TLS**: All API communications encrypted
- **Data Validation**: Input validation and sanitization
- **Secure Storage**: Sensitive data stored in device keychain

## 🚀 Performance Optimizations

- **Image Optimization**: Compressed images and lazy loading
- **Code Splitting**: Optimized bundle size
- **Caching**: API response caching for offline support
- **Memory Management**: Efficient state management
- **Background Tasks**: Optimized background processing

## 🔄 Updates and Maintenance

- **Over-the-Air Updates**: Use CodePush for instant updates
- **Version Management**: Semantic versioning for releases
- **Crash Reporting**: Integrated crash analytics
- **Performance Monitoring**: Real-time performance tracking

## 📞 Support

For technical support or questions:
- Email: support@laborlooker.com
- Documentation: [https://docs.laborlooker.com](https://docs.laborlooker.com)
- Issues: Create GitHub issues for bug reports

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.