// client/src/components/layout/Layout.tsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { notificationApi } from '../../api/api';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState<boolean>(false);
  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);

  useEffect(() => {
    // Close sidebar on mobile when route changes
    setSidebarOpen(false);
  }, [location]);

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

  // Function to get navigation items based on user role
  const getNavItems = () => {
    if (!isAuthenticated || !user) return [];

    const navItems = [
      { name: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
      { name: 'Tenders', path: '/tenders', icon: 'business_center' },
    ];

    if (user.role === 'admin' || user.role === 'staff') {
      navItems.push(
        { name: 'Create Tender', path: '/tenders/create', icon: 'add_circle' },
        { name: 'Vendors', path: '/vendors', icon: 'store' },
        { name: 'Reports', path: '/reports', icon: 'assessment' }
      );
    }

    if (user.role === 'admin') {
      navItems.push({ name: 'Users', path: '/users', icon: 'people' });
    }

    if (user.role === 'vendor') {
      navItems.push({ name: 'My Offers', path: '/offers', icon: 'local_offer' });
    }

    if (user.role === 'evaluator') {
      navItems.push({ name: 'Evaluations', path: '/evaluations', icon: 'grade' });
    }

    return navItems;
  };

  // If not authenticated, just render the children without the layout
  if (!isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed inset-y-0 left-0 z-30 w-64 bg-gradient-to-b from-blue-800 to-blue-600 transition duration-300 ease-in-out transform md:translate-x-0 md:static md:inset-0`}
      >
        <div className="flex items-center justify-center h-16 px-6 bg-blue-900">
          <Link to="/dashboard" className="flex items-center">
            <img src="/src/assets/aadf-logo-new.svg" alt="AADF Logo" className="h-8 w-auto mr-2" />
            <span className="text-white font-bold">Procurement</span>
          </Link>
        </div>
        <nav className="mt-5 px-2">
          {getNavItems().map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`group flex items-center px-2 py-2 text-base font-medium rounded-md ${
                location.pathname === item.path
                  ? 'bg-blue-700 text-white'
                  : 'text-blue-100 hover:bg-blue-700'
              }`}
            >
              <span className="material-icons mr-3 text-blue-300 group-hover:text-blue-100">
                {item.icon}
              </span>
              {item.name}
            </Link>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-white shadow-sm z-10">
          <div className="flex items-center justify-between h-16 px-6">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-600 focus:outline-none md:hidden"
            >
              <span className="material-icons">menu</span>
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
                  <div className="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
                    <div className="py-1 divide-y divide-gray-100">
                      <div className="px-4 py-2 text-sm text-gray-700 font-medium">Notifications</div>
                      <div className="max-h-96 overflow-y-auto">
                        {/* Notification items would go here */}
                        <div className="px-4 py-3 text-sm text-gray-700">
                          <p className="text-center">Click to view all notifications</p>
                        </div>
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
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
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