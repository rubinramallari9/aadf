// Updated Sidebar.tsx with ability to be toggled on all screen sizes
import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const location = useLocation();

  // Function to get navigation items based on user role
  const getNavItems = () => {
    if (!user) return [];

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

  // Sidebar positioning and visibility
  // Using absolute positioning instead of fixed for more flexibility
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
         
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <div className="space-y-1">
            {getNavItems().map((item) => (
              <Link
                key={item.path}
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