// client/src/pages/Home.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import { tenderApi } from '../api/api';

const Home: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const [publicTenders, setPublicTenders] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [stats, setStats] = useState({
    totalTenders: 0,
    activeTenders: 0,
    totalVendors: 0,
    successfulBids: 0,
  });

  useEffect(() => {
    const fetchPublicData = async () => {
      try {
        setLoading(true);
        
        // Fetch published tenders
        const response = await tenderApi.getAll({ status: 'published' });
        
        // Check if response is an array, if not, it might be in a 'results' property
        const tenders = Array.isArray(response) ? response : 
                       (response.results ? response.results : []);
        
        // Take only the first 5 tenders
        setPublicTenders(tenders.slice(0, 5)); 
        
        // Mock stats data for now (you can replace with actual API calls)
        setStats({
          totalTenders: 150,
          activeTenders: tenders.length,
          totalVendors: 75,
          successfulBids: 120,
        });
      } catch (error) {
        console.error('Error fetching public data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPublicData();
  }, []);

  const features = [
    {
      title: 'Transparent Process',
      description: 'Open and transparent procurement process with real-time updates.',
      icon: 'visibility',
    },
    {
      title: 'Secure Platform',
      description: 'Secure document sharing and submission with encryption.',
      icon: 'security',
    },
    {
      title: 'Fair Competition',
      description: 'Equal opportunities for all eligible vendors to participate.',
      icon: 'balance',
    },
    {
      title: 'Digital Transformation',
      description: 'Paperless procurement process saving time and resources.',
      icon: 'computer',
    },
  ];

  const benefits = [
    'Streamlined submission process',
    'Real-time status updates',
    'Automated evaluation system',
    'Secure document management',
    'Compliance with procurement laws',
    'Mobile-friendly interface',
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-grow">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-blue-700 to-blue-900 text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
            <div className="text-center">
              <h1 className="text-4xl md:text-5xl font-bold mb-6">
                AADF Procurement Platform
              </h1>
              <p className="text-xl mb-8 max-w-3xl mx-auto">
                Modernizing agricultural development procurement through transparency,
                efficiency, and digital innovation.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                {isAuthenticated ? (
                  <Link
                    to="/dashboard"
                    className="px-8 py-3 bg-white text-blue-900 rounded-lg font-semibold hover:bg-gray-100 transition"
                  >
                    Go to Dashboard
                  </Link>
                ) : (
                  <>
                    <Link
                      to="/register"
                      className="px-8 py-3 bg-white text-blue-900 rounded-lg font-semibold hover:bg-gray-100 transition"
                    >
                      Register as Vendor
                    </Link>
                    <Link
                      to="/tenders"
                      className="px-8 py-3 border-2 border-white text-white rounded-lg font-semibold hover:bg-white hover:text-blue-900 transition"
                    >
                      Browse Tenders
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="bg-gray-50 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-900">{stats.totalTenders}</div>
                <div className="text-gray-600">Total Tenders</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-900">{stats.activeTenders}</div>
                <div className="text-gray-600">Active Tenders</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-900">{stats.totalVendors}</div>
                <div className="text-gray-600">Registered Vendors</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-900">{stats.successfulBids}</div>
                <div className="text-gray-600">Successful Bids</div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Why Choose Our Platform?
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Experience the benefits of digital procurement with our state-of-the-art platform.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              {features.map((feature, index) => (
                <div key={index} className="bg-white p-6 rounded-lg shadow-md">
                  <div className="text-blue-600 mb-4">
                    <span className="material-icons text-4xl">{feature.icon}</span>
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Latest Tenders Section */}
        <div className="bg-gray-50 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900">Latest Tenders</h2>
              <Link
                to="/tenders"
                className="text-blue-600 hover:text-blue-800 font-semibold"
              >
                View All Tenders →
              </Link>
            </div>
            {loading ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {publicTenders.map((tender) => (
                  <div key={tender.id} className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="text-lg font-semibold">{tender.title}</h3>
                      <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
                        {tender.status}
                      </span>
                    </div>
                    <p className="text-gray-600 mb-4 line-clamp-2">{tender.description}</p>
                    <div className="flex justify-between items-center text-sm text-gray-500">
                      <span>Deadline: {new Date(tender.submission_deadline).toLocaleDateString()}</span>
                      <Link
                        to={`/tenders/${tender.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Details →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Benefits Section */}
        <div className="py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div>
                <h2 className="text-3xl font-bold text-gray-900 mb-6">
                  Benefits for Vendors
                </h2>
                <p className="text-xl text-gray-600 mb-8">
                  Join our platform and experience the advantages of digital procurement
                  in the agricultural sector.
                </p>
                <ul className="space-y-4">
                  {benefits.map((benefit, index) => (
                    <li key={index} className="flex items-center">
                      <span className="material-icons text-green-600 mr-3">check_circle</span>
                      <span className="text-gray-700">{benefit}</span>
                    </li>
                  ))}
                </ul>
                {!isAuthenticated && (
                  <div className="mt-8">
                    <Link
                      to="/register"
                      className="inline-block px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
                    >
                      Get Started Now
                    </Link>
                  </div>
                )}
              </div>
              <div className="hidden lg:block">
                <img
                  src="/src/assets/agriculture-illustration.svg"
                  alt="Agricultural Procurement"
                  className="w-full h-auto"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="bg-blue-900 text-white py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Transform Your Procurement Process?
            </h2>
            <p className="text-xl mb-8 max-w-2xl mx-auto">
              Join hundreds of vendors already benefiting from our digital procurement platform.
            </p>
            {!isAuthenticated && (
              <Link
                to="/register"
                className="inline-block px-8 py-3 bg-white text-blue-900 rounded-lg font-semibold hover:bg-gray-100 transition"
              >
                Register as Vendor
              </Link>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Home;