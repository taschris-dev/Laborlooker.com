import React, { useState } from 'react';
import { View, StyleSheet, Alert, ScrollView } from 'react-native';
import { TextInput, Button, Title, Paragraph, HelperText } from 'react-native-paper';
import { Picker } from '@react-native-picker/picker';
import { useAuth } from '../../contexts/AuthContext';

const RegisterScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    accountType: 'customer',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  
  const { register, loading, error, clearError } = useAuth();

  const updateFormData = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 15) {
      newErrors.password = 'Password must be at least 15 characters long';
    } else if (!/[A-Z].*[A-Z]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least 2 uppercase letters';
    } else if (!/[!@_\-.]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one symbol (!@_-.)';
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // Account type validation
    if (!formData.accountType) {
      newErrors.accountType = 'Please select an account type';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRegister = async () => {
    if (!validateForm()) return;

    clearError();
    
    const result = await register({
      email: formData.email.trim(),
      password: formData.password,
      account_type: formData.accountType,
    });
    
    if (result.success) {
      Alert.alert(
        'Registration Successful',
        result.message || 'Please check your email to verify your account.',
        [
          {
            text: 'OK',
            onPress: () => navigation.navigate('Login'),
          },
        ]
      );
    } else {
      Alert.alert('Registration Failed', result.error || 'Please try again.');
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Title style={styles.title}>Create Account</Title>
        <Paragraph style={styles.subtitle}>
          Join LaborLooker to connect with professionals
        </Paragraph>
      </View>

      <View style={styles.form}>
        <TextInput
          label="Email"
          value={formData.email}
          onChangeText={(value) => updateFormData('email', value)}
          mode="outlined"
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
          style={styles.input}
          error={!!errors.email}
        />
        <HelperText type="error" visible={!!errors.email}>
          {errors.email}
        </HelperText>

        <TextInput
          label="Password"
          value={formData.password}
          onChangeText={(value) => updateFormData('password', value)}
          mode="outlined"
          secureTextEntry={!showPassword}
          style={styles.input}
          error={!!errors.password}
          right={
            <TextInput.Icon
              icon={showPassword ? 'eye-off' : 'eye'}
              onPress={() => setShowPassword(!showPassword)}
            />
          }
        />
        <HelperText type="error" visible={!!errors.password}>
          {errors.password}
        </HelperText>

        <TextInput
          label="Confirm Password"
          value={formData.confirmPassword}
          onChangeText={(value) => updateFormData('confirmPassword', value)}
          mode="outlined"
          secureTextEntry={!showConfirmPassword}
          style={styles.input}
          error={!!errors.confirmPassword}
          right={
            <TextInput.Icon
              icon={showConfirmPassword ? 'eye-off' : 'eye'}
              onPress={() => setShowConfirmPassword(!showConfirmPassword)}
            />
          }
        />
        <HelperText type="error" visible={!!errors.confirmPassword}>
          {errors.confirmPassword}
        </HelperText>

        <View style={styles.pickerContainer}>
          <Paragraph style={styles.pickerLabel}>Account Type</Paragraph>
          <View style={styles.picker}>
            <Picker
              selectedValue={formData.accountType}
              onValueChange={(value) => updateFormData('accountType', value)}
              style={styles.pickerStyle}
            >
              <Picker.Item label="Customer (I need work done)" value="customer" />
              <Picker.Item label="Contractor (I provide services)" value="contractor" />
            </Picker>
          </View>
        </View>
        <HelperText type="error" visible={!!errors.accountType}>
          {errors.accountType}
        </HelperText>

        <View style={styles.passwordRequirements}>
          <Paragraph style={styles.requirementsTitle}>Password Requirements:</Paragraph>
          <Paragraph style={styles.requirement}>• At least 15 characters long</Paragraph>
          <Paragraph style={styles.requirement}>• At least 2 uppercase letters</Paragraph>
          <Paragraph style={styles.requirement}>• At least one symbol (!@_-.)</Paragraph>
        </View>

        {error && (
          <HelperText type="error" visible={true} style={styles.errorText}>
            {error}
          </HelperText>
        )}

        <Button
          mode="contained"
          onPress={handleRegister}
          loading={loading}
          disabled={loading}
          style={styles.button}
          contentStyle={styles.buttonContent}
        >
          Create Account
        </Button>
      </View>

      <View style={styles.footer}>
        <Paragraph style={styles.footerText}>
          Already have an account?{' '}
        </Paragraph>
        <Button
          mode="text"
          onPress={() => navigation.navigate('Login')}
          compact
        >
          Sign in here
        </Button>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 20,
    paddingVertical: 20,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#2196F3',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
  },
  form: {
    flex: 1,
  },
  input: {
    marginBottom: 8,
  },
  pickerContainer: {
    marginBottom: 16,
  },
  pickerLabel: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  picker: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 4,
  },
  pickerStyle: {
    height: 50,
  },
  passwordRequirements: {
    backgroundColor: '#f5f5f5',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
  },
  requirementsTitle: {
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  requirement: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  button: {
    marginTop: 24,
    borderRadius: 8,
  },
  buttonContent: {
    paddingVertical: 8,
  },
  errorText: {
    textAlign: 'center',
    marginBottom: 16,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
  },
  footerText: {
    color: '#666',
  },
});

export default RegisterScreen;