import React, { useRef } from 'react';
import { Camera, Sparkles, Download, LogOut, Undo2 } from 'lucide-react';
import useStore from '../utils/store';
import { uploadGardenImage, exportPlantList } from '../utils/api';

export default function Navbar() {
  const fileRef = useRef(null);
  const {
    user, logout, gardenImage, setGardenImage,
    placedPlants, setShowStyleModal, isGenerating,
  } = useStore();

  const hasAIRender = gardenImage?.originalUrl && gardenImage.url !== gardenImage.originalUrl;

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await uploadGardenImage(file);
      setGardenImage(result);
    } catch {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setGardenImage({ id: 'local', url: ev.target.result, width: 900, height: 600 });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRevert = () => {
    if (gardenImage?.originalUrl) {
      setGardenImage({
        ...gardenImage,
        url: gardenImage.originalUrl,
        generatedUrl: gardenImage.generatedUrl,
      });
    }
  };

  const handleExport = async () => {
    try {
      await exportPlantList(placedPlants, 'csv');
    } catch {
      const counts = {};
      const plants = useStore.getState().plants;
      placedPlants.forEach(p => {
        const plant = plants.find(pl => pl.id === p.plant_id);
        if (plant) counts[plant.name] = (counts[plant.name] || 0) + 1;
      });
      let csv = 'Plant Name,Quantity,Category\n';
      Object.entries(counts).forEach(([name, qty]) => {
        const plant = plants.find(p => p.name === name);
        csv += `"${name}",${qty},"${plant?.category || ''}"\n`;
      });
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'paysagea-garden-plan.csv'; a.click();
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>Paysagea</h1>
        <span className="navbar-badge">Garden Designer</span>
      </div>

      <div className="navbar-actions">
        <button className="btn-toolbar warm" onClick={() => fileRef.current?.click()}>
          <Camera size={15} /> Upload Photo
        </button>
        <input ref={fileRef} type="file" accept="image/*" onChange={handleUpload} style={{ display: 'none' }} />

        {hasAIRender && (
          <button className="btn-toolbar" onClick={handleRevert} title="Revert to original photo">
            <Undo2 size={15} /> Original
          </button>
        )}

        <button
          className="btn-toolbar primary"
          disabled={!gardenImage || isGenerating}
          onClick={() => setShowStyleModal(true)}
        >
          <Sparkles size={15} />
          {isGenerating ? 'Designing…' : 'AI Auto-Design'}
        </button>

        <button className="btn-toolbar" disabled={placedPlants.length === 0} onClick={handleExport}>
          <Download size={15} /> Export List
        </button>

        <div className="navbar-divider" />

        <div className="navbar-avatar" title={user}>
          {user?.[0]?.toUpperCase() || 'U'}
        </div>

        <button className="btn-toolbar" onClick={logout} style={{ padding: '9px 12px' }} title="Sign out">
          <LogOut size={15} />
        </button>
      </div>
    </nav>
  );
}
