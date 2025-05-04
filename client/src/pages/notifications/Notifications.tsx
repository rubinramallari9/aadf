// Fixed Notifications.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../contexts/AuthContext';
import { notificationApi } from '../api/api';

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  related_entity_type?: string;
  related_entity_id?: number;
  created_at: string;
}

const Notifications: React.FC = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all'); // 'all', 'unread', 'read'

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await notificationApi.getAll();
      
      // Check if response is an array before sorting
      if (Array.isArray(response)) {
        // Sort notifications by date (newest first)
        const sortedNotifications = [...response].sort((a: Notification, b: Notification) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        
        setNotifications(sortedNotifications);
      } else {
        // Handle case where response might have a different structure
        // For example, if it has a 'results' property containing the notifications
        if (response && response.results && Array.isArray(response.results)) {
          const sortedNotifications = [...response.results].sort((a: Notification, b: Notification) => {
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
          });
          
          setNotifications(sortedNotifications);
        } else {
          // If response has an unexpected format, set an empty array
          console.error('Unexpected response format:', response);
          setNotifications([]);
        }
      }
    } catch (err: any) {
      console.error('Error fetching notifications:', err);
      setError(err.message || 'Failed to load notifications');
      // Ensure we set notifications to an empty array when there's an error
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await notificationApi.markAsRead(notificationId);
      
      // Update the notification in state
      setNotifications(notifications.map(notification => 
        notification.id === notificationId 
          ? { ...notification, is_read: true } 
          : notification
      ));
    } catch (err: any) {
      console.error('Error marking notification as read:', err);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      
      // Update all notifications in state
      setNotifications(notifications.map(notification => ({ ...notification, is_read: true })));
    } catch (err: any) {
      console.error('Error marking all notifications as read:', err);
    }
  };

  // Filter notifications based on selected filter
  const filteredNotifications = notifications.filter(notification => {
    if (filter === 'all') return true;
    if (filter === 'unread') return !notification.is_read;
    if (filter === 'read') return notification.is_read;
    return true;
  });

  // Get notification type color
  const getNotificationTypeColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'info':
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  // Get entity link based on entity type and id
  const getEntityLink = (entityType: string | undefined, entityId: number | undefined) => {
    if (!entityType || !entityId) return null;
    
    switch (entityType) {
      case 'tender':
        return `/tenders/${entityId}`;
      case 'offer':
        return `/offers/${entityId}`;
      case 'vendor':
        return `/vendors/${entityId}`;
      case 'user':
        return `/users/${entityId}`;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="flex justify-between items-center p-6 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
            
            <div className="flex items-center space-x-2">
              <div className="relative">
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="pl-3 pr-10 py-2 text-sm border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md"
                >
                  <option value="all">All</option>
                  <option value="unread">Unread</option>
                  <option value="read">Read</option>
                </select>
              </div>
              
              <button
                onClick={handleMarkAllAsRead}
                className="px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
              >
                Mark all as read
              </button>
            </div>
          </div>
          
          <div className="divide-y divide-gray-200">
            {filteredNotifications.length > 0 ? (
              filteredNotifications.map((notification) => (
                <div 
                  key={notification.id} 
                  className={`p-6 ${notification.is_read ? 'bg-white' : 'bg-blue-50'}`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getNotificationTypeColor(notification.type)}`}>
                          {notification.type}
                        </span>
                        <span className="ml-3 text-sm text-gray-500">
                          {new Date(notification.created_at).toLocaleString()}
                        </span>
                      </div>
                      <h3 className="mt-1 text-lg font-medium text-gray-900">{notification.title}</h3>
                      <p className="mt-1 text-gray-600">{notification.message}</p>
                      
                      {notification.related_entity_type && notification.related_entity_id && (
                        <div className="mt-2">
                          <Link
                            to={getEntityLink(notification.related_entity_type, notification.related_entity_id) || '#'}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            View related {notification.related_entity_type}
                          </Link>
                        </div>
                      )}
                    </div>
                    
                    {!notification.is_read && (
                      <button
                        onClick={() => handleMarkAsRead(notification.id)}
                        className="ml-4 text-blue-600 hover:text-blue-800"
                      >
                        <span className="material-icons">check_circle</span>
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 text-center text-gray-500">
                <span className="material-icons text-4xl">notifications_off</span>
                <p className="mt-2">No notifications found</p>
                {filter !== 'all' && (
                  <p className="mt-1">
                    <button 
                      onClick={() => setFilter('all')} 
                      className="text-blue-600 hover:text-blue-800"
                    >
                      Show all notifications
                    </button>
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Notifications;