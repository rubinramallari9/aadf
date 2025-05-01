// Updated Layout.tsx with toggle functionality for all screen sizes
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { notificationApi } from '../../api/api';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [notifications, setNotifications] = useState<any[]>([]);
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true); // Default open on desktop
  const [profileDropdownOpen, setProfileDropdownOpen] = useState<boolean>(false);
  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);

  // Check screen size on initial load and window resize
  useEffect(() => {
    const checkScreenSize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false); // Default closed on mobile
      }
    };
    
    // Check on initial load
    checkScreenSize();
    
    // Add resize listener
    window.addEventListener('resize', checkScreenSize);
    
    // Clean up
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  // Fetch unread notifications count
  useEffect(() => {
    if (isAuthenticated) {
      const fetchUnreadCount = async () => {
        try {
          const response = await notificationApi.getUnreadCount();
          setUnreadCount(response.count);
        } catch (error) {
          console.error('Failed to fetch unread count:', error);
        }
      };

      fetchUnreadCount();

      // Set up interval to check for new notifications
      const interval = setInterval(fetchUnreadCount, 60000); // Every minute
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await notificationApi.getAll();
      // Sort by date (newest first) and filter to get only the recent ones
      const sortedNotifications = response
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5); // Get only the 5 most recent
      
      setNotifications(sortedNotifications);
      const unreadCount = response.filter((n: any) => !n.is_read).length;
      setUnreadCount(unreadCount);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  };
  

  // If not authenticated, just render the children without the layout
  if (!isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar component */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden ${sidebarOpen ? 'md:ml-64' : 'ml-0'}`}>
        {/* Top Bar */}
        <header className="bg-white shadow-sm z-10">
          <div className="flex items-center justify-between h-16 px-6">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-600 focus:outline-none"
            >
              <span className="material-icons">
                {sidebarOpen ? 'menu_open' : 'menu'}
              </span>
            </button>

            <div className="flex items-center">
              {/* Notifications dropdown */}
              <div className="relative mr-4">
                <button
                  onClick={() => setNotificationsOpen(!notificationsOpen)}
                  className="relative p-1 text-gray-600 hover:text-blue-600 focus:outline-none"
                >
                  <span className="material-icons">notifications</span>
                  {unreadCount > 0 && (
                    <span className="absolute top-0 right-0 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                </button>
                {notificationsOpen && (
                  <div className="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1 divide-y divide-gray-100">
                      <div className="px-4 py-2 text-sm text-gray-700 font-medium flex justify-between items-center">
                        <span>Notifications</span>
                        <button 
                          onClick={async (e) => {
                            e.stopPropagation();
                            try {
                              await notificationApi.markAllAsRead();
                              setUnreadCount(0);
                            } catch (error) {
                              console.error('Failed to mark all as read:', error);
                            }
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          Mark all as read
                        </button>
                      </div>
                      <div className="max-h-96 overflow-y-auto">
                        {notifications.length > 0 ? (
                          notifications.slice(0, 5).map(notification => (
                            <div 
                              key={notification.id} 
                              className={`px-4 py-3 hover:bg-gray-50 ${notification.is_read ? '' : 'bg-blue-50'}`}
                            >
                              <div className="flex justify-between">
                                <p className="text-sm font-medium text-gray-900 truncate">{notification.title}</p>
                                {!notification.is_read && (
                                  <button
                                    onClick={async (e) => {
                                      e.stopPropagation();
                                      try {
                                        await notificationApi.markAsRead(notification.id);
                                        setNotifications(prev => 
                                          prev.map(n => n.id === notification.id ? {...n, is_read: true} : n)
                                        );
                                        setUnreadCount(prev => Math.max(0, prev - 1));
                                      } catch (error) {
                                        console.error('Failed to mark as read:', error);
                                      }
                                    }}
                                    className="text-blue-600 hover:text-blue-800"
                                  >
                                    <span className="material-icons text-sm">check_circle</span>
                                  </button>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-1">{new Date(notification.created_at).toLocaleString()}</p>
                              <p className="text-sm text-gray-600 mt-1 truncate">{notification.message}</p>
                            </div>
                          ))
                        ) : (
                          <div className="px-4 py-3 text-sm text-gray-700">
                            <p className="text-center">No notifications</p>
                          </div>
                        )}
                      </div>
                      <div className="px-4 py-2">
                        <Link
                          to="/notifications"
                          className="block text-sm text-center text-blue-600 hover:text-blue-800"
                          onClick={() => setNotificationsOpen(false)}
                        >
                          View all notifications
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Profile dropdown */}
              <div className="relative">
                <button
                  onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                  className="flex items-center text-gray-600 hover:text-blue-600 focus:outline-none"
                >
                  <span className="material-icons mr-1">account_circle</span>
                  <span className="hidden md:block">{user?.username}</span>
                  <span className="material-icons">arrow_drop_down</span>
                </button>
                {profileDropdownOpen && (
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1">
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setProfileDropdownOpen(false)}
                      >
                        Your Profile
                      </Link>
                      <Link
                        to="/change-password"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setProfileDropdownOpen(false)}
                      >
                        Change Password
                      </Link>
                      <button
                        onClick={() => {
                          setProfileDropdownOpen(false);
                          handleLogout();
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;