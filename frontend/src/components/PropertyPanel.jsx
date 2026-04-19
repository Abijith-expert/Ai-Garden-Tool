import React from 'react';
import { Trash2, FlipHorizontal, RotateCw } from 'lucide-react';
import useStore from '../utils/store';

export default function PropertyPanel() {
  const { plants, placedPlants, selectedId, updatePlacedPlant, removePlacedPlant } = useStore();

  const item = placedPlants.find((p) => p.id === selectedId);
  const plant = item ? plants.find((p) => p.id === item.plant_id) : null;

  if (!item || !plant) {
    return (
      <div className="property-panel">
        <div className="property-empty">
          <div className="property-empty-icon">🌱</div>
          <div>Select a plant on the canvas to edit its properties</div>
        </div>
      </div>
    );
  }

  const imgSrc = plant.image_url || `/static/plants/${plant.filename}`;

  return (
    <div className="property-panel">
      <div style={{
        width: 80, height: 80, margin: '0 auto 16px',
        borderRadius: 12, background: 'var(--bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'
      }}>
        <img src={imgSrc} alt={plant.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
      </div>

      <div className="property-title">{plant.name}</div>
      <div className="property-meta">
        {plant.height_cm}cm tall · {plant.spread_cm}cm spread<br />
        {plant.sun} · {plant.water} water · {plant.category}
      </div>

      {/* Scale */}
      <div className="property-slider-group">
        <div className="property-slider-label">
          <span>Scale</span>
          <span>{Math.round(item.scale * 100)}%</span>
        </div>
        <input
          type="range"
          className="property-slider"
          min="0.2" max="2.5" step="0.05"
          value={item.scale}
          onChange={(e) => updatePlacedPlant(item.id, { scale: parseFloat(e.target.value) })}
        />
      </div>

      {/* Rotation */}
      <div className="property-slider-group">
        <div className="property-slider-label">
          <span>Rotation</span>
          <span>{Math.round(item.rotation || 0)}°</span>
        </div>
        <input
          type="range"
          className="property-slider"
          min="-15" max="15" step="1"
          value={item.rotation || 0}
          onChange={(e) => updatePlacedPlant(item.id, { rotation: parseFloat(e.target.value) })}
        />
      </div>

      {/* Flip */}
      <button
        className="btn-toolbar"
        style={{ width: '100%', justifyContent: 'center', marginBottom: 10 }}
        onClick={() => updatePlacedPlant(item.id, { flip_h: !item.flip_h })}
      >
        <FlipHorizontal size={14} />
        Flip Horizontal {item.flip_h ? '(On)' : ''}
      </button>

      {/* Delete */}
      <button className="btn-danger" onClick={() => removePlacedPlant(item.id)}>
        <Trash2 size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
        Remove Plant
      </button>
    </div>
  );
}
