import React from 'react';
import Navbar from '../components/Navbar';
import PlantSidebar from '../components/PlantSidebar';
import DesignCanvas from '../components/DesignCanvas';
import StyleModal from '../components/StyleModal';
import useStore from '../utils/store';

export default function DesignerPage() {
  const { isGenerating } = useStore();

  return (
    <div className="app-layout">
      <Navbar />
      <div className="main-content">
        <PlantSidebar />
        <DesignCanvas />
      </div>
      <StyleModal />
      {isGenerating && (
        <div className="overlay">
          <div className="overlay-card">
            <div className="overlay-spinner">🌿</div>
            <div className="overlay-title">Designing your garden…</div>
            <div className="overlay-subtitle">
              AI is analyzing your space and placing plants with natural clustering
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
