import React, { useState, useEffect } from 'react';
import { FacilityData, EventData } from '../types';
import { api } from '../services/api';
import { Image, ExternalLink, ShieldCheck, MapPin, Calendar, Layers, Sparkles } from 'lucide-react';

export const VisualGalleryView: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<'all' | 'facilities' | 'events'>('all');
  const [facilities, setFacilities] = useState<FacilityData[]>([]);
  const [events, setEvents] = useState<EventData[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadGallery();
  }, []);

  const loadGallery = async () => {
    setIsLoading(true);
    try {
      const [facData, evData] = await Promise.all([
        api.getFacilities(),
        api.getEvents()
      ]);
      setFacilities(facData);
      setEvents(evData);
    } catch (err) {
      console.error('Error loading visual gallery:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="font-heading text-2xl font-bold text-white flex items-center space-x-2">
            <Image className="w-6 h-6 text-ait-500" />
            <span>AIT Official Visual Archives & Gallery</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real, authentic photography sourced strictly from official Ahmedabad Institute of Technology portals
          </p>
        </div>

        {/* Filter Switcher */}
        <div className="flex items-center space-x-1 glass-card p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveCategory('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeCategory === 'all' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Media
          </button>
          <button
            onClick={() => setActiveCategory('facilities')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeCategory === 'facilities' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Campus & Facilities
          </button>
          <button
            onClick={() => setActiveCategory('events')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeCategory === 'events' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Historical Events (2024-25)
          </button>
        </div>
      </div>

      {/* Facilities Cards */}
      {(activeCategory === 'all' || activeCategory === 'facilities') && (
        <div className="space-y-4">
          <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
            <Layers className="w-5 h-5 text-ait-500" />
            <span>Institutional Facilities & Infrastructure</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {facilities.map(fac => (
              <div key={fac.id} className="glass-card rounded-2xl overflow-hidden border border-slate-800 flex flex-col justify-between group">
                <div>
                  {fac.images.length > 0 && (
                    <div className="relative h-56 bg-slate-900 overflow-hidden">
                      <img
                        src={fac.images[0].image_url}
                        alt={fac.images[0].alt_text || fac.name}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />
                      <div className="absolute top-3 right-3 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 backdrop-blur-md flex items-center space-x-1">
                        <ShieldCheck className="w-3 h-3 text-emerald-400" />
                        <span>Verified Real Image</span>
                      </div>
                      <div className="absolute bottom-3 left-4 right-4">
                        <h4 className="font-heading text-lg font-bold text-white leading-tight">{fac.name}</h4>
                        <p className="text-xs text-ait-200 flex items-center space-x-1 mt-0.5">
                          <MapPin className="w-3.5 h-3.5" />
                          <span>{fac.location || 'AIT Campus'}</span>
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="p-5">
                    <p className="text-xs text-slate-300 leading-relaxed">{fac.description}</p>
                    <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-800">
                      <span>Timings: {fac.timings}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                        {fac.category}
                      </span>
                    </div>
                  </div>
                </div>

                {fac.images.length > 0 && (
                  <div className="px-5 py-3 bg-slate-900/60 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate">{fac.images[0].source_page}</span>
                    <a
                      href={fac.images[0].source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ait-200 hover:text-white flex items-center space-x-1 flex-shrink-0"
                    >
                      <span>View Provenance</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical Events Gallery */}
      {(activeCategory === 'all' || activeCategory === 'events') && (
        <div className="space-y-4 pt-4">
          <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
            <Calendar className="w-5 h-5 text-ait-gold" />
            <span>Official Historical Events (2024 & 2025)</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {events.map(ev => (
              <div key={ev.id} className="glass-card rounded-2xl overflow-hidden border border-slate-800 flex flex-col justify-between group">
                <div>
                  {ev.images.length > 0 && (
                    <div className="relative h-48 bg-slate-900 overflow-hidden">
                      <img
                        src={ev.images[0].image_url}
                        alt={ev.images[0].alt_text || ev.name}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />
                      <div className="absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 backdrop-blur-md">
                        {ev.calendar_year}
                      </div>
                      <div className="absolute bottom-2 left-3 right-3">
                        <h4 className="font-heading text-base font-bold text-white leading-tight">{ev.name}</h4>
                        <p className="text-[11px] text-slate-300">{ev.event_type} • {ev.organizer}</p>
                      </div>
                    </div>
                  )}

                  <div className="p-4">
                    <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">{ev.description}</p>
                    <div className="mt-3 text-[11px] text-slate-400">
                      <strong>Date:</strong> {ev.date_start}
                    </div>
                  </div>
                </div>

                <div className="px-4 py-2.5 bg-slate-900/60 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                  <span className="truncate">Official Event Portal</span>
                  <a
                    href={ev.official_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-ait-200 hover:text-white flex items-center space-x-1 flex-shrink-0"
                  >
                    <span>Archive Link</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
