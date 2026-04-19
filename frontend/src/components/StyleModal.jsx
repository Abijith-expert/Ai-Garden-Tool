import React, { useState } from 'react';
import useStore from '../utils/store';
import { generateDesign, generateGardenImage } from '../utils/api';

const STYLES = [
  { key: 'natural', icon: '🌿', label: 'Natural' },
  { key: 'formal', icon: '🏛️', label: 'Formal' },
  { key: 'cottage', icon: '🌷', label: 'Cottage' },
  { key: 'modern', icon: '🔲', label: 'Modern' },
  { key: 'tropical', icon: '🌴', label: 'Tropical' },
  { key: 'mediterranean', icon: '☀️', label: 'Mediterranean' },
];

const DENSITIES = [
  { key: 'sparse', label: 'Sparse' },
  { key: 'medium', label: 'Medium' },
  { key: 'dense', label: 'Dense' },
];

export default function StyleModal() {
  const {
    showStyleModal, setShowStyleModal,
    gardenImage, plants,
    setPlacedPlants, setGardenImage, setIsGenerating,
  } = useStore();

  const [style, setStyle] = useState('natural');
  const [density, setDensity] = useState('medium');
  const [mode, setMode] = useState('render'); // 'render' = AI image gen, 'cutout' = placement
  const [error, setError] = useState('');

  if (!showStyleModal) return null;

  const handleGenerate = async () => {
    setShowStyleModal(false);
    setIsGenerating(true);
    setPlacedPlants([]);
    setError('');

    if (mode === 'render') {
      // ── AI Image Generation (like Gemini) ──
      try {
        const result = await generateGardenImage(gardenImage.id, style, density);
        // Replace the garden image with the AI-generated one
        setGardenImage({
          ...gardenImage,
          url: result.url,
          generatedUrl: result.url,
          originalUrl: gardenImage.originalUrl || gardenImage.url,
          width: result.width,
          height: result.height,
        });
      } catch (err) {
        console.warn('AI render failed, falling back to cutout mode:', err.message);
        // Fallback to cutout placement
        await doCutoutPlacement();
      }
    } else {
      // ── Cutout Placement Mode ──
      await doCutoutPlacement();
    }

    setIsGenerating(false);
  };

  const doCutoutPlacement = async () => {
    let placements = [];
    try {
      const result = await generateDesign(gardenImage.id, style, density, []);
      placements = result.placements || [];
    } catch {
      placements = clientFallback(plants, style, density);
    }

    for (let i = 0; i < placements.length; i++) {
      await new Promise((r) => setTimeout(r, 80));
      useStore.setState((s) => ({
        placedPlants: [...s.placedPlants, placements[i]],
      }));
    }
  };

  return (
    <div className="overlay" onClick={() => setShowStyleModal(false)}>
      <div className="style-modal" onClick={(e) => e.stopPropagation()}>
        <h2>AI Garden Design</h2>
        <p>Choose a generation mode, style, and density.</p>

        {/* Mode Toggle */}
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Generation Mode
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <button
            onClick={() => setMode('render')}
            style={{
              flex: 1, padding: '14px 12px',
              border: mode === 'render' ? '2px solid var(--accent)' : '1.5px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              background: mode === 'render' ? 'var(--accent-light)' : 'var(--card)',
              cursor: 'pointer', fontFamily: 'var(--font-body)',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, marginBottom: 6 }}>🎨</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Rendered Image</div>
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>
              Server composites plants onto<br />your photo with shadows & blending
            </div>
          </button>
          <button
            onClick={() => setMode('cutout')}
            style={{
              flex: 1, padding: '14px 12px',
              border: mode === 'cutout' ? '2px solid var(--accent)' : '1.5px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              background: mode === 'cutout' ? 'var(--accent-light)' : 'var(--card)',
              cursor: 'pointer', fontFamily: 'var(--font-body)',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 24, marginBottom: 6 }}>🌿</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Interactive Cutouts</div>
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>
              Draggable plant PNGs on photo<br />(editable after placement)
            </div>
          </button>
        </div>

        {/* Style Grid */}
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Style
        </div>
        <div className="style-grid">
          {STYLES.map((s) => (
            <button
              key={s.key}
              className={`style-option ${style === s.key ? 'selected' : ''}`}
              onClick={() => setStyle(s.key)}
            >
              <div className="style-option-icon">{s.icon}</div>
              <div className="style-option-label">{s.label}</div>
            </button>
          ))}
        </div>

        {/* Density */}
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Density
        </div>
        <div className="density-row">
          {DENSITIES.map((d) => (
            <button
              key={d.key}
              className={`density-btn ${density === d.key ? 'selected' : ''}`}
              onClick={() => setDensity(d.key)}
            >
              {d.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ padding: 10, background: 'var(--danger-bg)', color: 'var(--danger)', borderRadius: 8, fontSize: 12, marginBottom: 12 }}>
            {error}
          </div>
        )}

        <div className="modal-actions">
          <button className="btn-cancel" onClick={() => setShowStyleModal(false)}>Cancel</button>
          <button className="btn-generate" onClick={handleGenerate}>
            {mode === 'render' ? '🎨 Render Garden' : '🌿 Place Plants'}
          </button>
        </div>
      </div>
    </div>
  );
}


// ─── Client-side fallback ───
function clientFallback(plants, style, density) {
  if (!plants.length) return [];
  const counts = { sparse: 14, medium: 24, dense: 36 };
  const target = counts[density] || 24;
  const result = [];

  const beds = [
    { cx: 22, cy: 72 }, { cx: 68, cy: 68 }, { cx: 45, cy: 76 },
    { cx: 15, cy: 60 }, { cx: 80, cy: 62 },
  ];

  for (let i = 0; i < target; i++) {
    const plant = plants[i % plants.length];
    const bed = beds[i % beds.length];
    const x = bed.cx + (Math.random() - 0.5) * 16;
    const y = bed.cy + (Math.random() - 0.5) * 10;

    result.push({
      id: `gd_${Date.now()}_${i}`,
      plant_id: plant.id,
      x_percent: +Math.max(3, Math.min(97, x)).toFixed(1),
      y_percent: +Math.max(45, Math.min(92, y)).toFixed(1),
      scale: +(0.5 + Math.random() * 0.5).toFixed(2),
      rotation: +((Math.random() - 0.5) * 6).toFixed(1),
      flip_h: Math.random() > 0.5,
    });
  }
  return result;
}
