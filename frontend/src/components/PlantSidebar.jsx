import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search } from 'lucide-react';
import useStore from '../utils/store';
import PropertyPanel from './PropertyPanel';

const CATEGORIES = [
  { key: 'all', label: 'All', icon: '🌍' },
  { key: 'flowers', label: 'Flowers', icon: '🌸' },
  { key: 'shrubs', label: 'Shrubs', icon: '🌿' },
  { key: 'trees', label: 'Trees', icon: '🌳' },
  { key: 'groundcover', label: 'Ground', icon: '🍀' },
  { key: 'ornamental', label: 'Ornamental', icon: '🌾' },
  { key: 'potted', label: 'Potted', icon: '🪴' },
  { key: 'hedges', label: 'Hedges', icon: '🪻' },
  { key: 'climbers', label: 'Climbers', icon: '🌱' },
];

const PAGE_SIZE = 40;

/** Lazy-loaded plant image — only loads src when visible */
function LazyPlantImage({ src, alt }) {
  const imgRef = useRef(null);
  const [loaded, setLoaded] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = imgRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '100px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={imgRef}
      style={{
        width: 44, height: 44,
        borderRadius: 'var(--radius-sm)',
        background: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {visible && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={(e) => { e.target.style.display = 'none'; }}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain',
            opacity: loaded ? 1 : 0,
            transition: 'opacity 0.2s',
          }}
        />
      )}
    </div>
  );
}

function PlantCard({ plant }) {
  const handleDragStart = (e) => {
    e.dataTransfer.setData('plantId', plant.id);
    e.dataTransfer.effectAllowed = 'copy';
  };

  const imgSrc = plant.image_url || `/static/plants/${plant.filename}`;

  return (
    <div className="plant-card" draggable onDragStart={handleDragStart}>
      <LazyPlantImage src={imgSrc} alt={plant.name} />
      <div className="plant-card-info">
        <div className="plant-card-name">{plant.name}</div>
        <div className="plant-card-meta">{plant.height_cm}cm · {plant.sun}</div>
      </div>
      <span className="plant-card-cat">{plant.category}</span>
    </div>
  );
}

export default function PlantSidebar() {
  const { plants, setPlants } = useStore();
  const [tab, setTab] = useState('plants');
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const listRef = useRef(null);
  const searchTimer = useRef(null);

  // Fetch plants from API with pagination
  const fetchPlants = useCallback(async (pageNum, cat, q, append = false) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(pageNum),
        limit: String(PAGE_SIZE),
      });
      if (cat && cat !== 'all') params.set('category', cat);
      if (q) params.set('search', q);

      const res = await fetch(`/api/plants?${params}`);
      const data = await res.json();

      if (append) {
        setPlants([...useStore.getState().plants, ...data.plants]);
      } else {
        setPlants(data.plants);
      }
      setTotalPages(data.pages);
      setTotal(data.total);
      setPage(pageNum);
    } catch {
      console.warn('Could not fetch plants from API');
    }
    setLoading(false);
  }, [setPlants]);

  // Initial load
  useEffect(() => {
    fetchPlants(1, category, search);
  }, []);

  // When category changes: reset and reload
  useEffect(() => {
    fetchPlants(1, category, search);
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [category]);

  // Debounced search
  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      fetchPlants(1, category, search);
      if (listRef.current) listRef.current.scrollTop = 0;
    }, 300);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  // Infinite scroll: load next page when scrolled to bottom
  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || loading || page >= totalPages) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100) {
      fetchPlants(page + 1, category, search, true);
    }
  }, [loading, page, totalPages, category, search, fetchPlants]);

  return (
    <aside className="sidebar">
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${tab === 'plants' ? 'active' : ''}`}
          onClick={() => setTab('plants')}
        >
          Plants {total > 0 ? `(${total})` : ''}
        </button>
        <button
          className={`sidebar-tab ${tab === 'properties' ? 'active' : ''}`}
          onClick={() => setTab('properties')}
        >
          Properties
        </button>
      </div>

      {tab === 'plants' ? (
        <div
          className="sidebar-body"
          ref={listRef}
          onScroll={handleScroll}
        >
          <div className="search-wrapper">
            <Search size={14} className="search-icon" />
            <input
              className="search-input"
              style={{ paddingLeft: 36 }}
              placeholder="Search plants…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="category-pills">
            {CATEGORIES.map((c) => (
              <button
                key={c.key}
                className={`category-pill ${category === c.key ? 'active' : ''}`}
                onClick={() => setCategory(c.key)}
              >
                {c.icon} {c.label}
              </button>
            ))}
          </div>

          <div className="plant-list">
            {plants.length === 0 && !loading ? (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                No plants found. Check that the backend is running and plants_dataset/ has images.
              </div>
            ) : (
              plants.map((p) => <PlantCard key={p.id} plant={p} />)
            )}

            {loading && (
              <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                Loading plants…
              </div>
            )}

            {!loading && page < totalPages && (
              <button
                onClick={() => fetchPlants(page + 1, category, search, true)}
                style={{
                  width: '100%', padding: 10, marginTop: 8,
                  background: 'var(--accent-light)', color: 'var(--accent)',
                  border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Load More ({total - plants.length} remaining)
              </button>
            )}
          </div>

          <div className="tip-card">
            <strong>Tip:</strong> Drag plants onto your garden photo. Plants auto-scale
            by depth — placed higher = smaller (farther away). Press Delete to remove selected.
          </div>
        </div>
      ) : (
        <div className="sidebar-body" style={{ padding: 0 }}>
          <PropertyPanel />
        </div>
      )}
    </aside>
  );
}
