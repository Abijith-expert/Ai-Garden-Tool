import React from 'react';
import useStore from './utils/store';
import AuthPage from './pages/AuthPage';
import DesignerPage from './pages/DesignerPage';

export default function App() {
  const user = useStore((s) => s.user);
  return user ? <DesignerPage /> : <AuthPage />;
}
