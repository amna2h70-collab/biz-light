import React, { useState, useRef, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import './index.css';

// Using local generated images that will be in the public folder
const getImg = (name) => `/${name}.png`;

const productsList = [
  { id: 1, name: "Aero X-1 Drone", sku: "TOY-DRONE-001", price: 35000, image: getImg('toy_drone'), category: "Tech Toys" },
  { id: 2, name: "Cyber Mech", sku: "TOY-ROBOT-002", price: 65000, image: getImg('toy_robot'), category: "Robotics" },
  { id: 3, name: "Neon Drift RC", sku: "TOY-CAR-004", price: 18500, image: getImg('toy_car'), category: "Remote Control" },
  { id: 4, name: "Space Rocket", sku: "TOY-ROCKET-011", price: 22000, image: getImg('toy_rocket'), category: "Exploration" },
  { id: 5, name: "Hoverboard 3000", sku: "TOY-HOVER-005", price: 45000, image: "https://images.pexels.com/photos/163036/mario-luigi-yoshi-figures-163036.jpeg?auto=compress&cs=tinysrgb&w=800", category: "Ride-on" },
  { id: 6, name: "VR Space Helmet", sku: "TOY-VR-006", price: 42000, image: "https://images.pexels.com/photos/3861458/pexels-photo-3861458.jpeg?auto=compress&cs=tinysrgb&w=800", category: "Virtual Reality" },
  { id: 7, name: "Plasma Blaster", sku: "TOY-BLASTER-007", price: 8500, image: "https://images.pexels.com/photos/13056158/pexels-photo-13056158.jpeg?auto=compress&cs=tinysrgb&w=800", category: "Action" },
  { id: 8, name: "Robo-Dog Buddy", sku: "TOY-DOG-008", price: 32000, image: "https://images.pexels.com/photos/255514/pexels-photo-255514.jpeg?auto=compress&cs=tinysrgb&w=800", category: "Robotics" }
];

// Context for Cart
const CartContext = createContext();

// Format PKR Currency
const formatPKR = (num) => new Intl.NumberFormat('en-PK', { style: 'currency', currency: 'PKR', minimumFractionDigits: 0 }).format(num);

// 3D Tilt Component
function TiltCard({ children }) {
  const cardRef = useRef(null);
  const [rotateX, setRotateX] = useState(0);
  const [rotateY, setRotateY] = useState(0);

  const handleMouseMove = (e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateXVal = ((y - centerY) / centerY) * -15;
    const rotateYVal = ((x - centerX) / centerX) * 15;
    setRotateX(rotateXVal);
    setRotateY(rotateYVal);
  };

  const handleMouseLeave = () => {
    setRotateX(0);
    setRotateY(0);
  };

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      animate={{ rotateX, rotateY }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{ transformStyle: "preserve-3d", height: "100%" }}
    >
      {children}
    </motion.div>
  );
}

function Home() {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
      <header className="hero">
        <h1>Welcome to <span className="logo-highlight">WonderToyz</span></h1>
        <p>Experience toys like never before. Scroll through our amazing 3D renders and grab the coolest gadgets on the planet.</p>
        <Link to="/products" style={{ textDecoration: 'none' }}>
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} style={{ display: 'inline-block' }}>
            <button className="cart-btn" style={{ fontSize: '1.4rem', padding: '1rem 3rem' }}>Explore Shop</button>
          </motion.div>
        </Link>
      </header>
    </motion.div>
  );
}

function Products() {
  const { addToCart } = useContext(CartContext);
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="products-grid">
      {productsList.map((product, i) => (
        <motion.div key={product.id} initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1, type: "spring" }}>
          <TiltCard>
            <div className="product-card">
              <div className="product-image-container">
                <img
                  src={product.image}
                  alt={product.name}
                  className="product-image"
                  onError={(e) => { e.target.src = "https://images.pexels.com/photos/163036/mario-luigi-yoshi-figures-163036.jpeg?auto=compress&cs=tinysrgb&w=800"; }}
                />
              </div>
              <div className="product-info">
                <span className="product-category">{product.category}</span>
                <h3 className="product-title">{product.name}</h3>
                <div className="product-bottom">
                  <span className="product-price">{formatPKR(product.price)}</span>
                  <button className="buy-btn" onClick={() => addToCart(product)}>+</button>
                </div>
              </div>
            </div>
          </TiltCard>
        </motion.div>
      ))}
    </motion.div>
  );
}

function Cart() {
  const { cart, removeFromCart, getCartTotal } = useContext(CartContext);
  const navigate = useNavigate();

  return (
    <motion.div initial={{ opacity: 0, x: -50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} style={{ padding: '2rem 0' }}>
      <h1 style={{ fontSize: '3rem', marginBottom: '2rem', textAlign: 'center' }}>Your <span className="logo-highlight">Cart</span></h1>

      {cart.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem', background: 'white', borderRadius: '30px', maxWidth: '600px', margin: '0 auto', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
          <h2 style={{ color: 'var(--text-light)' }}>Cart is empty 🛒</h2>
          <Link to="/products"><button className="cart-btn" style={{ marginTop: '2rem' }}>Go Shopping</button></Link>
        </div>
      ) : (
        <div style={{ maxWidth: '800px', margin: '0 auto', background: 'white', borderRadius: '30px', padding: '2rem', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
          {cart.map((item, idx) => (
            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem 0', borderBottom: '1px solid #edf2f7' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <img src={item.image} alt={item.name} style={{ width: '60px', height: '60px', objectFit: 'contain', background: '#f7fafc', borderRadius: '10px' }} />
                <div>
                  <h3 style={{ fontSize: '1.2rem', margin: 0 }}>{item.name}</h3>
                  <span style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>{item.sku}</span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
                <strong style={{ fontSize: '1.2rem', color: 'var(--primary)' }}>{formatPKR(item.price)}</strong>
                <button onClick={() => removeFromCart(idx)} style={{ background: '#e2e8f0', border: 'none', width: '30px', height: '30px', borderRadius: '15px', cursor: 'pointer', fontWeight: 'bold' }}>X</button>
              </div>
            </div>
          ))}
          <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '2rem' }}>Total: <span className="logo-highlight">{formatPKR(getCartTotal())}</span></h2>
            <button className="cart-btn" style={{ padding: '1rem 3rem', fontSize: '1.2rem' }} onClick={() => navigate('/checkout')}>
              Proceed to Checkout 🚀
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function Checkout() {
  const { cart, getCartTotal, clearCart, showToast } = useContext(CartContext);
  const [isProcessing, setIsProcessing] = useState(false);
  const navigate = useNavigate();

  const handleCheckout = async (e) => {
    e.preventDefault();
    if (cart.length === 0) return;
    setIsProcessing(true);

    try {
      // Save order to the Store's Local Database (json-server)
      for (const item of cart) {
        await fetch('http://localhost:3001/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sku: item.sku,
            name: item.name,
            price: item.price,
            quantity: 1,
            customerName: e.target[0].value,
            email: e.target[1].value,
            status: "Pending",
            timestamp: new Date().toISOString()
          })
        });
      }
      showToast('Order Saved to Store DB! Waiting for Biz-Light Sync.', 'success');
      clearCart();
      setTimeout(() => navigate('/'), 2000);
    } catch (err) {
      console.error(err);
      showToast('Error syncing with backend database.', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  if (cart.length === 0) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2>No items to checkout.</h2></div>;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem 0' }}>
      <div style={{ background: 'white', padding: '3rem', borderRadius: '30px', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
        <h1 style={{ marginBottom: '2rem', textAlign: 'center' }}>Checkout</h1>
        <form onSubmit={handleCheckout} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <input type="text" placeholder="Full Name" required style={{ padding: '1rem', borderRadius: '15px', border: '2px solid #e2e8f0', fontSize: '1.1rem' }} />
          <input type="email" placeholder="Email Address" required style={{ padding: '1rem', borderRadius: '15px', border: '2px solid #e2e8f0', fontSize: '1.1rem' }} />
          <input type="text" placeholder="Shipping Address" required style={{ padding: '1rem', borderRadius: '15px', border: '2px solid #e2e8f0', fontSize: '1.1rem' }} />
          <div style={{ padding: '1.5rem', background: '#f7fafc', borderRadius: '15px', marginTop: '1rem' }}>
            <h3>Order Summary</h3>
            <p>Total Items: {cart.length}</p>
            <h2 style={{ color: 'var(--primary)', marginTop: '0.5rem' }}>Total: {formatPKR(getCartTotal())}</h2>
          </div>
          <button type="submit" className="cart-btn" disabled={isProcessing} style={{ padding: '1.2rem', fontSize: '1.3rem', marginTop: '1rem' }}>
            {isProcessing ? 'Processing Order...' : 'Confirm Purchase'}
          </button>
        </form>
      </div>
    </motion.div>
  );
}

function StoreSettings() {
  const STORE_API_KEY = 'test_store_key_123';
  const STORE_ENDPOINT = 'http://localhost:3001/orders';
  const [copied, setCopied] = useState('');

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ maxWidth: '700px', margin: '0 auto', padding: '2rem 0' }}>
      <div style={{ background: 'white', padding: '3rem', borderRadius: '30px', boxShadow: '0 20px 40px rgba(0,0,0,0.05)' }}>
        <h1 style={{ marginBottom: '0.5rem', textAlign: 'center' }}>🔐 Store <span className="logo-highlight">Settings</span></h1>
        <p style={{ textAlign: 'center', color: '#718096', marginBottom: '2rem', fontSize: '0.95rem' }}>
          Use these credentials to connect your store to <strong>Biz-Light AI Co-Manager</strong>.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ padding: '1.5rem', background: '#f7fafc', borderRadius: '15px', border: '2px solid #e2e8f0' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 800, color: '#a0aec0', textTransform: 'uppercase', letterSpacing: '1px' }}>Your API Key</label>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem' }}>
              <code style={{ fontSize: '1.1rem', fontWeight: 700, color: '#2d3748', fontFamily: 'monospace' }}>{STORE_API_KEY}</code>
              <button
                onClick={() => copyToClipboard(STORE_API_KEY, 'key')}
                style={{ background: copied === 'key' ? '#48bb78' : '#667eea', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '0.85rem' }}>
                {copied === 'key' ? '✓ Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          <div style={{ padding: '1.5rem', background: '#f7fafc', borderRadius: '15px', border: '2px solid #e2e8f0' }}>
            <label style={{ fontSize: '0.8rem', fontWeight: 800, color: '#a0aec0', textTransform: 'uppercase', letterSpacing: '1px' }}>Orders API Endpoint</label>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem' }}>
              <code style={{ fontSize: '1rem', fontWeight: 700, color: '#2d3748', fontFamily: 'monospace' }}>{STORE_ENDPOINT}</code>
              <button
                onClick={() => copyToClipboard(STORE_ENDPOINT, 'url')}
                style={{ background: copied === 'url' ? '#48bb78' : '#667eea', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '0.85rem' }}>
                {copied === 'url' ? '✓ Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          <div style={{ padding: '1.5rem', background: 'linear-gradient(135deg, #667eea22, #764ba222)', borderRadius: '15px', border: '2px dashed #cbd5e0', marginTop: '0.5rem' }}>
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>📋 How to connect to Biz-Light:</h3>
            <ol style={{ paddingLeft: '1.2rem', color: '#4a5568', lineHeight: '1.8', fontSize: '0.9rem' }}>
              <li>Log in to your <strong>Biz-Light Dashboard</strong></li>
              <li>Go to <strong>Integrations</strong> in the sidebar</li>
              <li>Select <strong>"Custom API"</strong> as platform type</li>
              <li>Paste the <strong>API Endpoint</strong> and <strong>API Key</strong> above</li>
              <li>Click <strong>Save Credentials</strong>, then <strong>Sync Store Data</strong></li>
            </ol>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function MainLayout() {
  const [toasts, setToasts] = useState([]);
  const [cart, setCart] = useState([]);
  const location = useLocation();

  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  };

  const addToCart = (product) => {
    setCart(prev => [...prev, product]);
    showToast(`Added ${product.name} to cart!`, 'success');
  };

  const removeFromCart = (index) => {
    setCart(prev => prev.filter((_, i) => i !== index));
  };

  const clearCart = () => setCart([]);
  const getCartTotal = () => cart.reduce((total, item) => total + item.price, 0);

  return (
    <CartContext.Provider value={{ cart, addToCart, removeFromCart, clearCart, getCartTotal, showToast }}>
      <div className="app-container">
        <nav className="navbar">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <div className="logo">🧸 <span className="logo-highlight">WonderToyz</span></div>
          </Link>
          <div className="nav-links">
            <Link to="/" className="nav-link">Home</Link>
            <Link to="/products" className="nav-link">Products</Link>
            <Link to="/settings" className="nav-link">Settings</Link>
            <Link to="/cart">
              <button className="cart-btn" style={{ padding: '0.5rem 1.2rem' }}>
                Cart ({cart.length})
              </button>
            </Link>
          </div>
        </nav>

        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Home />} />
            <Route path="/products" element={<Products />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/settings" element={<StoreSettings />} />
          </Routes>
        </AnimatePresence>

        <div className="toast-container">
          <AnimatePresence>
            {toasts.map(toast => (
              <motion.div key={toast.id} initial={{ opacity: 0, x: 100 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 100 }} className={`toast ${toast.type}`}>
                {toast.type === 'success' ? '🎉' : '⚠️'} {toast.message}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </CartContext.Provider>
  );
}

export default function App() {
  return (
    <Router>
      <MainLayout />
    </Router>
  );
}
