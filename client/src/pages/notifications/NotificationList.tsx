// client/src/pages/notifications/NotificationList.tsx
import React, { useState, useEffect } from 'react';
import Layout from '../../components/layout/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { notificationApi } from '../../api/api';

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
  related_object_type?: string;
  related_object_id?: number;
}

const NotificationList: React.FC = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  // Load notifications on component mount
  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await notificationApi.getAll();
      
      // Handle different response formats
      let notificationsData: Notification[] = [];
      if (Array.isArray(response)) {
        notificationsData = response;
      } else if (response?.results && Array.isArray(response.results)) {
        notificationsData = response.results;
      }
      
      // Sort by date, newest first
      notificationsData.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      
      setNotifications(notificationsData);
    } catch (err: any) {
      console.error('Error fetching notifications:', err);
      setError(err.message || 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await notificationApi.markAsRead(notificationId);
      
      // Update local state
      setNotifications(prev => 
        prev.map(notification => 
          notification.id === notificationId 
            ? { ...notification, is_read: true } 
            : notification
        )
      );
    } catch (err: any) {
      console.error('Error marking notification as read:', err);
      setError(err.message || 'Failed to mark notification as read');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      
      // Update local state
      setNotifications(prev => 
        prev.map(notification => ({ ...notification, is_read: true }))
      );
      
      setSuccess('All notifications marked as read');
      
      // Clear success message after a few seconds
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (err: any) {
      console.error('Error marking all notifications as read:', err);
      setError(err.message || 'Failed to mark all notifications as read');
    }
  };

  // Get filtered notifications
  const filteredNotifications = filter === 'unread'
    ? notifications.filter(notification => !notification.is_read)
    : notifications;

  // Get notification type styling
  const getNotificationTypeStyles = (type: string) => {
    switch (type) {
      case 'info':
        return 'bg-blue-100 text-blue-800';
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (!user) {
    return (
      <Layout>
        <div className="bg-yellow-50 border border-yellow-400 text-yellow-700 px-4 py-3 rounded-lg shadow-sm" role="alert">
          <div className="flex items-center">
            <span className="material-icons mr-2">info</span>
            <strong className="font-bold">Authentication Required</strong>
          </div>
          <span className="block sm:inline mt-1"> Please log in to view your notifications.</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <div className="flex items-center space-x-4">
            <div className="flex border border-gray-300 rounded-md p-1">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1 text-sm rounded-md ${
                  filter === 'all' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter('unread')}
                className={`px-3 py-1 text-sm rounded-md ${
                  filter === 'unread' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                Unread
              </button>
            </div>
            
            <button
              onClick={handleMarkAllAsRead}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={!notifications.some(n => !n.is_read)}
            >
              <span className="material-icons text-sm mr-1">done_all</span>
              Mark All as Read
            </button>
          </div>
        </div>
        
        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        
        {success && (
          <div className="mb-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{success}</span>
          </div>
        )}
        
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
          </div>
        ) : filteredNotifications.length > 0 ? (
          <div className="space-y-4">
            {filteredNotifications.map((notification) => (
              <div 
                key={notification.id} 
                className={`bg-white rounded-lg shadow-sm overflow-hidden border-l-4 ${
                  notification.is_read ? 'border-gray-300' : 'border-blue-500'
                }`}
              >
                <div className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center mb-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getNotificationTypeStyles(notification.type)}`}>
                          {notification.type}
                        </span>
                        {!notification.is_read && (
                          <span className="ml-2 w-2 h-2 rounded-full bg-blue-600"></span>
                        )}
                      </div>
                      <h3 className={`text-lg font-medium ${notification.is_read ? 'text-gray-700' : 'text-gray-900'}`}>
                        {notification.title}
                      </h3>
                      <p className="mt-1 text-sm text-gray-600">{notification.message}</p>
                      <div className="mt-2 text-xs text-gray-500">
                        {formatDate(notification.created_at)}
                      </div>
                    </div>
                    {!notification.is_read && (
                      <button
                        onClick={() => handleMarkAsRead(notification.id)}
                        className="ml-4 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                      >
                        <span className="material-icons text-sm mr-1">check</span>
                        Mark as read
                      </button>
                    )}
                  </div>
                  
                  {/* Action links based on related object type */}
                  {notification.related_object_type && notification.related_object_id && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <div className="flex">
                        {notification.related_object_type === 'tender' && (
                          <a
                            href={`/tenders/${notification.related_object_id}`}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            View Tender
                          </a>
                        )}
                        {notification.related_object_type === 'offer' && (
                          <a
                            href={`/offers/${notification.related_object_id}`}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            View Offer
                          </a>
                        )}
                        {notification.related_object_type === 'evaluation' && (
                          <a
                            href={`/evaluations/${notification.related_object_id}`}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            View Evaluation
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="flex justify-center mb-4">
              <span className="material-icons text-gray-400 text-5xl">notifications_none</span>
            </div>
            <h3 className="text-lg font-medium text-gray-900">No notifications</h3>
            <p className="mt-1 text-sm text-gray-500">
              {filter === 'unread' 
                ? 'You have no unread notifications.'
                : 'You don\'t have any notifications yet.'}
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default NotificationList;