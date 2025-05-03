// client/src/components/layout/Sidebar.tsx
import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// Define NavItem interface to include a key property
interface NavItem {
  name: string;
  path: string;
  icon: string;
  key?: string; // Optional unique key property
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const location = useLocation();

  // Function to get navigation items based on user role
  const getNavItems = (): NavItem[] => {
    if (!user) return [];

    const navItems: NavItem[] = [
      { name: 'Dashboard', path: '/dashboard', icon: 'dashboard', key: 'nav-dashboard' },
      { name: 'Tenders', path: '/tenders', icon: 'business_center', key: 'nav-tenders' },
    ];

    // Add Admin Dashboard link only for admin users, with a unique key
    if (user.role === 'admin') {
      navItems.unshift({ 
        name: 'Admin Dashboard', 
        path: '/admin', 
        icon: 'admin_panel_settings',
        key: 'nav-admin-dashboard'  // Unique key for admin dashboard
      });
    }

    if (user.role === 'admin' || user.role === 'staff') {
      navItems.push(
        { name: 'Create Tender', path: '/tenders/create', icon: 'add_circle', key: 'nav-create-tender' },
        { name: 'Vendors', path: '/vendors', icon: 'store', key: 'nav-vendors' },
        { name: 'Reports', path: '/reports', icon: 'assessment', key: 'nav-reports' }
      );
    }

    if (user.role === 'admin') {
      navItems.push({ name: 'Users', path: '/users', icon: 'people', key: 'nav-users' });
    }

    if (user.role === 'vendor') {
      navItems.push({ name: 'My Offers', path: '/offers', icon: 'local_offer', key: 'nav-offers' });
    }

    if (user.role === 'evaluator') {
      navItems.push({ name: 'Evaluations', path: '/evaluations', icon: 'grade', key: 'nav-evaluations' });
    }

    return navItems;
  };

  // Sidebar positioning and visibility
  const sidebarClasses = `
    absolute md:absolute inset-y-0 left-0 z-30 w-64 bg-gradient-to-b from-blue-800 to-blue-600 
    transform transition-transform duration-300 ease-in-out h-full
    ${isOpen ? 'translate-x-0' : '-translate-x-full'}
  `;

  return (
    <>
      {/* Overlay for mobile and desktop when sidebar is open */}
      {isOpen && (
        <div 
          className="md:hidden fixed inset-0 z-20 bg-black bg-opacity-50 transition-opacity" 
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div className={sidebarClasses}>
        {/* Logo and header */}
        <div className="flex items-center justify-between h-16 px-6 bg-blue-900">
          <Link to="/dashboard" className="flex items-center">
            <img src="/src/assets/aadf-logo-new.svg" alt="AADF Logo" className="h-8 w-auto mr-2 filter brightness-0 invert" />
          </Link>
          <button 
            onClick={onClose}
            className="text-white md:hidden"
          >
            <span className="material-icons">close</span>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <div className="space-y-1">
            {getNavItems().map((item) => (
              <Link
                key={item.key || `nav-item-${item.path}`} // Use the unique key or generate one from the path
                to={item.path}
                className={`
                  group flex items-center px-3 py-2 text-base font-medium rounded-md 
                  transition-colors duration-150 ease-in-out
                  ${location.pathname === item.path
                    ? 'bg-blue-700 text-white'
                    : 'text-blue-100 hover:bg-blue-700 hover:text-white'}
                `}
              >
                <span className={`
                  material-icons mr-3 
                  ${location.pathname === item.path
                    ? 'text-white'
                    : 'text-blue-300 group-hover:text-blue-100'}
                `}>
                  {item.icon}
                </span>
                {item.name}
              </Link>
            ))}
          </div>
        </nav>

        {/* Footer with user info */}
        <div className="p-4 border-t border-blue-700">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <span className="material-icons text-blue-300">account_circle</span>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-white">
                {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username}
              </p>
              <p className="text-xs text-blue-300">
                {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'Unknown'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;