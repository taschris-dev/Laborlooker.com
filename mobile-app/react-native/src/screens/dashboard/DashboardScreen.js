import React, { useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { Card, Title, Paragraph, Button, Chip, Avatar } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useAuth } from '../../contexts/AuthContext';
import { useApp } from '../../contexts/AppContext';

const DashboardScreen = ({ navigation }) => {
  const { user } = useAuth();
  const { stats, workRequests, loadWorkRequests, loading } = useApp();
  
  const isContractor = user?.account_type === 'contractor';
  const isCustomer = user?.account_type === 'customer';

  useEffect(() => {
    loadWorkRequests();
  }, []);

  const onRefresh = () => {
    loadWorkRequests();
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#4CAF50';
      case 'pending': return '#FF9800';
      case 'assigned': return '#2196F3';
      case 'cancelled': return '#F44336';
      default: return '#666';
    }
  };

  const recentRequests = workRequests?.slice(0, 3) || [];

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={onRefresh} />
      }
    >
      {/* Welcome Section */}
      <Card style={styles.welcomeCard}>
        <Card.Content>
          <View style={styles.welcomeHeader}>
            <Avatar.Icon 
              size={60} 
              icon="account" 
              style={styles.avatar}
            />
            <View style={styles.welcomeText}>
              <Title style={styles.greeting}>
                {getGreeting()}, {user?.profile?.first_name || user?.profile?.contact_name || 'User'}!
              </Title>
              <Paragraph style={styles.userType}>
                {isContractor ? 'Contractor Dashboard' : 'Customer Dashboard'}
              </Paragraph>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Statistics Cards */}
      {stats && (
        <View style={styles.statsContainer}>
          <Card style={styles.statCard}>
            <Card.Content style={styles.statContent}>
              <Icon name="work" size={32} color="#2196F3" />
              <Title style={styles.statNumber}>{stats.total_requests || 0}</Title>
              <Paragraph style={styles.statLabel}>
                {isContractor ? 'Total Jobs' : 'Total Requests'}
              </Paragraph>
            </Card.Content>
          </Card>

          <Card style={styles.statCard}>
            <Card.Content style={styles.statContent}>
              <Icon name="check-circle" size={32} color="#4CAF50" />
              <Title style={styles.statNumber}>{stats.completed_requests || 0}</Title>
              <Paragraph style={styles.statLabel}>Completed</Paragraph>
            </Card.Content>
          </Card>

          {isContractor && (
            <Card style={styles.statCard}>
              <Card.Content style={styles.statContent}>
                <Icon name="trending-up" size={32} color="#FF9800" />
                <Title style={styles.statNumber}>
                  {stats.completion_rate ? `${Math.round(stats.completion_rate)}%` : '0%'}
                </Title>
                <Paragraph style={styles.statLabel}>Success Rate</Paragraph>
              </Card.Content>
            </Card>
          )}

          {isCustomer && (
            <Card style={styles.statCard}>
              <Card.Content style={styles.statContent}>
                <Icon name="pending" size={32} color="#FF9800" />
                <Title style={styles.statNumber}>{stats.active_requests || 0}</Title>
                <Paragraph style={styles.statLabel}>Active</Paragraph>
              </Card.Content>
            </Card>
          )}
        </View>
      )}

      {/* Quick Actions */}
      <Card style={styles.actionsCard}>
        <Card.Content>
          <Title style={styles.sectionTitle}>Quick Actions</Title>
          <View style={styles.actionsContainer}>
            {isCustomer && (
              <Button
                mode="contained"
                icon="add"
                onPress={() => navigation.navigate('WorkRequests', { screen: 'CreateWorkRequest' })}
                style={styles.actionButton}
              >
                New Request
              </Button>
            )}
            
            <Button
              mode="outlined"
              icon="search"
              onPress={() => navigation.navigate(isCustomer ? 'Contractors' : 'WorkRequests')}
              style={styles.actionButton}
            >
              {isCustomer ? 'Find Contractors' : 'View Jobs'}
            </Button>
            
            <Button
              mode="outlined"
              icon="receipt"
              onPress={() => navigation.navigate('Invoices')}
              style={styles.actionButton}
            >
              Billing
            </Button>
          </View>
        </Card.Content>
      </Card>

      {/* Recent Work Requests */}
      {recentRequests.length > 0 && (
        <Card style={styles.recentCard}>
          <Card.Content>
            <View style={styles.sectionHeader}>
              <Title style={styles.sectionTitle}>
                Recent {isContractor ? 'Jobs' : 'Requests'}
              </Title>
              <Button
                mode="text"
                onPress={() => navigation.navigate('WorkRequests')}
                compact
              >
                View All
              </Button>
            </View>
            
            {recentRequests.map((request) => (
              <View key={request.id} style={styles.requestItem}>
                <View style={styles.requestHeader}>
                  <Paragraph style={styles.requestTitle}>
                    {request.title || 'Work Request'}
                  </Paragraph>
                  <Chip
                    style={[styles.statusChip, { backgroundColor: getStatusColor(request.status) }]}
                    textStyle={styles.statusText}
                  >
                    {request.status}
                  </Chip>
                </View>
                <Paragraph style={styles.requestDescription} numberOfLines={2}>
                  {request.description}
                </Paragraph>
                <Paragraph style={styles.requestDate}>
                  {new Date(request.created_at).toLocaleDateString()}
                </Paragraph>
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      {/* Empty State */}
      {recentRequests.length === 0 && (
        <Card style={styles.emptyCard}>
          <Card.Content style={styles.emptyContent}>
            <Icon 
              name={isCustomer ? "add-circle-outline" : "work-outline"} 
              size={64} 
              color="#ccc" 
            />
            <Title style={styles.emptyTitle}>
              {isCustomer ? 'No Requests Yet' : 'No Jobs Yet'}
            </Title>
            <Paragraph style={styles.emptyText}>
              {isCustomer 
                ? 'Create your first work request to get started.'
                : 'Available jobs will appear here when customers post them.'
              }
            </Paragraph>
            {isCustomer && (
              <Button
                mode="contained"
                onPress={() => navigation.navigate('WorkRequests', { screen: 'CreateWorkRequest' })}
                style={styles.emptyButton}
              >
                Create First Request
              </Button>
            )}
          </Card.Content>
        </Card>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  welcomeCard: {
    margin: 16,
    marginBottom: 8,
  },
  welcomeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    backgroundColor: '#2196F3',
    marginRight: 16,
  },
  welcomeText: {
    flex: 1,
  },
  greeting: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  userType: {
    color: '#666',
    fontSize: 14,
  },
  statsContainer: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 8,
  },
  statCard: {
    flex: 1,
    marginHorizontal: 4,
  },
  statContent: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    marginVertical: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  actionsCard: {
    margin: 16,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  actionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    marginBottom: 8,
    minWidth: '30%',
  },
  recentCard: {
    margin: 16,
    marginBottom: 8,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  requestItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  requestHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  requestTitle: {
    fontWeight: 'bold',
    flex: 1,
    marginRight: 8,
  },
  statusChip: {
    height: 24,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
  },
  requestDescription: {
    color: '#666',
    marginBottom: 4,
  },
  requestDate: {
    fontSize: 12,
    color: '#999',
  },
  emptyCard: {
    margin: 16,
  },
  emptyContent: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginBottom: 24,
  },
  emptyButton: {
    paddingHorizontal: 24,
  },
});

export default DashboardScreen;