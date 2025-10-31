import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../contexts/AuthContext';

// Screens
import DashboardScreen from '../screens/dashboard/DashboardScreen';
import WorkRequestsScreen from '../screens/workRequests/WorkRequestsScreen';
import CreateWorkRequestScreen from '../screens/workRequests/CreateWorkRequestScreen';
import WorkRequestDetailScreen from '../screens/workRequests/WorkRequestDetailScreen';
import ContractorSearchScreen from '../screens/contractors/ContractorSearchScreen';
import ContractorDetailScreen from '../screens/contractors/ContractorDetailScreen';
import InvoicesScreen from '../screens/invoices/InvoicesScreen';
import InvoiceDetailScreen from '../screens/invoices/InvoiceDetailScreen';
import ProfileScreen from '../screens/profile/ProfileScreen';
import EditProfileScreen from '../screens/profile/EditProfileScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

// Stack navigators for each tab
const DashboardStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="DashboardMain" 
      component={DashboardScreen}
      options={{ title: 'Dashboard' }}
    />
  </Stack.Navigator>
);

const WorkRequestsStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="WorkRequestsList" 
      component={WorkRequestsScreen}
      options={{ title: 'Work Requests' }}
    />
    <Stack.Screen 
      name="CreateWorkRequest" 
      component={CreateWorkRequestScreen}
      options={{ title: 'New Work Request' }}
    />
    <Stack.Screen 
      name="WorkRequestDetail" 
      component={WorkRequestDetailScreen}
      options={{ title: 'Request Details' }}
    />
  </Stack.Navigator>
);

const ContractorsStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="ContractorSearch" 
      component={ContractorSearchScreen}
      options={{ title: 'Find Contractors' }}
    />
    <Stack.Screen 
      name="ContractorDetail" 
      component={ContractorDetailScreen}
      options={{ title: 'Contractor Details' }}
    />
  </Stack.Navigator>
);

const InvoicesStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="InvoicesList" 
      component={InvoicesScreen}
      options={{ title: 'Invoices' }}
    />
    <Stack.Screen 
      name="InvoiceDetail" 
      component={InvoiceDetailScreen}
      options={{ title: 'Invoice Details' }}
    />
  </Stack.Navigator>
);

const ProfileStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="ProfileMain" 
      component={ProfileScreen}
      options={{ title: 'Profile' }}
    />
    <Stack.Screen 
      name="EditProfile" 
      component={EditProfileScreen}
      options={{ title: 'Edit Profile' }}
    />
    <Stack.Screen 
      name="Settings" 
      component={SettingsScreen}
      options={{ title: 'Settings' }}
    />
  </Stack.Navigator>
);

const MainNavigator = () => {
  const { user } = useAuth();
  const isContractor = user?.account_type === 'contractor';
  const isCustomer = user?.account_type === 'customer';

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          switch (route.name) {
            case 'Dashboard':
              iconName = 'dashboard';
              break;
            case 'WorkRequests':
              iconName = isContractor ? 'work' : 'add-circle';
              break;
            case 'Contractors':
              iconName = 'search';
              break;
            case 'Invoices':
              iconName = 'receipt';
              break;
            case 'Profile':
              iconName = 'person';
              break;
            default:
              iconName = 'help';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardStack}
        options={{ title: 'Home' }}
      />
      
      <Tab.Screen 
        name="WorkRequests" 
        component={WorkRequestsStack}
        options={{ 
          title: isContractor ? 'Jobs' : 'Requests'
        }}
      />
      
      {isCustomer && (
        <Tab.Screen 
          name="Contractors" 
          component={ContractorsStack}
          options={{ title: 'Find Help' }}
        />
      )}
      
      <Tab.Screen 
        name="Invoices" 
        component={InvoicesStack}
        options={{ title: 'Billing' }}
      />
      
      <Tab.Screen 
        name="Profile" 
        component={ProfileStack}
        options={{ title: 'Profile' }}
      />
    </Tab.Navigator>
  );
};

export default MainNavigator;