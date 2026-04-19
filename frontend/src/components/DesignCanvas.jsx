import React, { useRef, useState, useCallback, useEffect } from 'react';
import useStore from '../utils/store';

/*
 * RENDERING RULES:
 * - y_percent = plant BASE on ground. Image grows UP from there.
 * - Depth: higher y% = closer to camera = bigger
 * - Plants at y=62% (back) are ~55% size, at y=92% (front) are ~100%
 */

function depthScale(yPct) {
  const t = Math.max(0, Math.min(1, (yPct - 50) / 50));
  return 0.5 + t * 0.5;
}

function dropShadow(yPct, scale) {
  const t = Math.max(0, Math.min(1, yPct / 100));
  const blur = 4 + t * 14;
  const oy = 2 + t * 8;
  const op = 0.12 + t * 0.2;
  return `drop-shadow(0px ${Math.round(oy * scale)}px ${Math.round(blur * scale)}px rgba(0,0,0,${op.toFixed(2)}))`;
}

const SIZES = {
  trees: { w: 350, h: 500 },
  hedges: { w: 300, h: 250 },
  shrubs: { w: 260, h: 280 },
  climbers: { w: 160, h: 400 },
  ornamental: { w: 220, h: 320 },
  flowers: { w: 200, h: 220 },
  potted: { w: 170, h: 190 },
  groundcover: { w: 300, h: 100 },
};

function PlacedPlant({ item, plant, cw, ch, selected, onSelect, onPointerStart, isDragging }) {
  const ds = depthScale(item.y_percent);
  const scale = (item.scale || 1) * ds;
  const sz = SIZES[plant.category] || { w: 200, h: 200 };
  const w = sz.w * scale;
  const h = sz.h * scale;

  const bx = (item.x_percent / 100) * cw;
  const by = (item.y_percent / 100) * ch;
  const left = bx - w / 2;
  const top = by - h;

  const z = Math.floor(item.y_percent) + 10;
  const rot = item.rotation || 0;
  const flipX = item.flip_h ? -1 : 1;
  const src = plant.image_url || `/static/plants/${plant.filename}`;
  const shadow = dropShadow(item.y_percent, scale);
  const imgFilter = 'brightness(0.92) contrast(1.04) sepia(0.03)';

  const shW = w * 0.8;
  const shH = Math.max(8, 16 * scale);

  return (
    <div
      className={`placed-plant ${selected ? 'selected' : ''} ${isDragging ? 'dragging' : ''}`}
      style={{
        left,
        top,
        width: w,
        height: h,
        zIndex: isDragging ? 9999 : z,
        filter: shadow,
        transform: `scaleX(${flipX}) rotate(${rot}deg)`,
        transformOrigin: 'bottom center',
      }}
      onPointerDown={(e) => onPointerStart(e, item, w, h)}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(item.id);
      }}
    >
      <img
        src={src}
        alt={plant.name}
        loading="lazy"
        draggable={false}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          objectPosition: 'bottom center',
          pointerEvents: 'none',
          userSelect: 'none',
          filter: imgFilter,
        }}
        onError={(e) => {
          e.target.style.display = 'none';
          e.target.parentElement.style.background = 'radial-gradient(ellipse at bottom, #5a8c4f, #3a6b35)';
          e.target.parentElement.style.borderRadius = '45% 45% 5% 5%';
          e.target.parentElement.style.opacity = '0.7';
        }}
      />

      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: '8%',
          width: '84%',
          height: '18%',
          background:
            'linear-gradient(to top, rgba(20,18,10,0.3) 0%, rgba(20,18,10,0.08) 50%, transparent 100%)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          position: 'absolute',
          bottom: -Math.round(shH * 0.3),
          left: (w - shW) / 2,
          width: shW,
          height: shH,
          background: 'radial-gradient(ellipse, rgba(0,0,0,0.28) 0%, rgba(0,0,0,0.1) 45%, transparent 75%)',
          borderRadius: '50%',
          pointerEvents: 'none',
          zIndex: -1,
          filter: 'blur(3px)',
        }}
      />
    </div>
  );
}

export default function DesignCanvas() {
  const ref = useRef(null);
  const dragRef = useRef(null);
  const [size, setSize] = useState({ w: 900, h: 600 });
  const [draggingId, setDraggingId] = useState(null);
  const {
    gardenImage,
    plants,
    placedPlants,
    addPlacedPlant,
    updatePlacedPlant,
    selectedId,
    setSelectedId,
    clearPlacedPlants,
  } = useStore();

  useEffect(() => {
    const measure = () => {
      if (ref.current) {
        const r = ref.current.getBoundingClientRect();
        setSize({ w: r.width, h: r.height });
      }
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [gardenImage]);

  const clampToCanvas = useCallback((clientX, clientY, offsetX, offsetY) => {
    if (!ref.current) return null;
    const rect = ref.current.getBoundingClientRect();

    const xPercent = ((clientX - rect.left - offsetX) / rect.width) * 100;
    const yPercent = ((clientY - rect.top - offsetY) / rect.height) * 100;

    return {
      x_percent: Math.max(2, Math.min(98, xPercent)),
      y_percent: Math.max(5, Math.min(98, yPercent)),
    };
  }, []);

  const stopDragging = useCallback(() => {
    dragRef.current = null;
    setDraggingId(null);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  const handlePointerMove = useCallback(
    (e) => {
      if (!dragRef.current) return;
      const next = clampToCanvas(
        e.clientX,
        e.clientY,
        dragRef.current.offsetX,
        dragRef.current.offsetY
      );
      if (!next) return;
      updatePlacedPlant(dragRef.current.id, next);
    },
    [clampToCanvas, updatePlacedPlant]
  );

  useEffect(() => {
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', stopDragging);
    window.addEventListener('pointercancel', stopDragging);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', stopDragging);
      window.removeEventListener('pointercancel', stopDragging);
    };
  }, [handlePointerMove, stopDragging]);

  const onPointerStart = useCallback((e, item, width, height) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedId(item.id);
    setDraggingId(item.id);
    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';
    dragRef.current = {
      id: item.id,
      offsetX: width / 2,
      offsetY: height,
    };
  }, [setSelectedId]);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      if (!ref.current) return;

      const plantId = e.dataTransfer.getData('plantId');
      if (!plantId) return;

      const rect = ref.current.getBoundingClientRect();
      addPlacedPlant({
        id: `placed_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        plant_id: plantId,
        x_percent: Math.max(2, Math.min(98, ((e.clientX - rect.left) / rect.width) * 100)),
        y_percent: Math.max(5, Math.min(98, ((e.clientY - rect.top) / rect.height) * 100)),
        scale: 1.0,
        rotation: 0,
        flip_h: false,
      });
    },
    [addPlacedPlant]
  );

  useEffect(() => {
    const fn = (e) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        useStore.getState().removePlacedPlant(selectedId);
      }
    };
    window.addEventListener('keydown', fn);
    return () => window.removeEventListener('keydown', fn);
  }, [selectedId]);

  return (
    <div className="canvas-area">
      <div className="canvas-toolbar">
        <span>
          {placedPlants.length} plant{placedPlants.length !== 1 ? 's' : ''} placed
          {selectedId ? ' · Drag to move · Delete to remove' : ''}
        </span>
        {placedPlants.length > 0 && (
          <button className="btn-clear" onClick={clearPlacedPlants}>
            Clear All
          </button>
        )}
      </div>

      <div
        ref={ref}
        className="canvas-wrapper"
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'copy';
        }}
        onClick={() => setSelectedId(null)}
      >
        {gardenImage?.url ? (
          <>
            <img src={gardenImage.url} alt="Garden" className="garden-image" draggable={false} />
            {placedPlants.map((item) => {
              const plant = plants.find((p) => p.id === item.plant_id);
              if (!plant) return null;
              return (
                <PlacedPlant
                  key={item.id}
                  item={item}
                  plant={plant}
                  cw={size.w}
                  ch={size.h}
                  selected={selectedId === item.id}
                  onSelect={setSelectedId}
                  onPointerStart={onPointerStart}
                  isDragging={draggingId === item.id}
                />
              );
            })}
          </>
        ) : (
          <div className="canvas-empty">
            <div className="canvas-empty-icon">📷</div>
            <h3>Upload your garden photo</h3>
            <p style={{ fontSize: 13.5 }}>Click "Upload Photo" to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
