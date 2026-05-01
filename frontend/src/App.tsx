/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Stethoscope, 
  Search, 
  AlertCircle, 
  AlertTriangle, 
  ChevronRight, 
  RotateCcw, 
  Activity, 
  CheckCircle2, 
  XCircle,
  PhoneCall,
  Info,
  ArrowLeft,
  LayoutGrid,
  HeartPulse,
  Clock,
  Coins,
  ShieldCheck,
  TrendingUp,
  Layout
} from 'lucide-react';

// --- Types ---

interface CostBreakdownItem {
  component: string;
  label: string;
  min: number;
  max: number;
}

interface CostEstimateResponse {
  condition_name: string;
  icd10: string;
  pathway_id: string;
  city: string;
  city_tier: string;
  hospital_type: string;
  combined_multiplier: number;
  breakdown: CostBreakdownItem[];
  total_min: number;
  total_max: number;
  total_range_label: string;
  insurance: {
    eligible: boolean;
    scheme: string;
    covered_amount: number;
    out_of_pocket_min: number;
    out_of_pocket_max: number;
    note: string;
  };
  notes: string;
  disclaimer: string;
}

interface Condition {
  id: string;
  name: string;
  icd10: string;
  pathway_id: string;
  confidence: number;
}

interface AnalysisResult {
  query: string;
  cleaned_query: string;
  extracted_symptoms: string[];
  negated_symptoms: string[];
  conditions: Condition[];
  top_condition: string | null;
  low_confidence: boolean;
  emergency_flag: boolean;
  emergency_message: string | null;
}

interface PathwayStep {
  id: string;
  order: number;
  name: string;
  type: string;
  mandatory: boolean;
  description: string;
  cost_tier: string;
  cost_tier_info: {
    label: string;
    range: string;
  };
}

interface ResolvedBranch {
  condition: string;
  label: string;
  steps: PathwayStep[];
}

interface PathwayResponse {
  pathway_id: string;
  condition: string;
  icd10: string;
  severity_requested: 'mild' | 'moderate' | 'severe';
  base_steps: PathwayStep[];
  branch_point?: {
    at_step_id: string;
    label: string;
  };
  resolved_branch?: ResolvedBranch;
  total_steps: number;
  has_surgery: boolean;
  mandatory_steps: any[];
  optional_steps: any[];
}

interface TradeoffTag {
  tag: string;
  icon: string;
  label: string;
}

interface Hospital {
  rank: number;
  id: string;
  name: string;
  city: string;
  state: string;
  type: string;
  type_label: string;
  rating: number;
  review_count: number;
  nabh_accredited: boolean;
  cost_category: string;
  cost_multiplier: number;
  distance_km: number;
  icu_available: boolean;
  emergency: boolean;
  bed_count: number;
  phone: string;
  tradeoff_tags: TradeoffTag[];
  final_score: number;
  score_breakdown: {
    rating_score: number;
    distance_score: number;
    type_score: number;
    nabh_bonus: number;
  };
  pm_jay_eligible: boolean;
}

interface ScoringWeights {
  rating: number;
  distance: number;
  type: number;
  nabh: number;
}

interface HospitalResponse {
  pathway_id: string;
  city: string;
  total_found: number;
  showing: number;
  scoring_weights: ScoringWeights;
  results: Hospital[];
}

interface AvailablePathway {
  id: string;
  name: string;
  category: string;
  pathway_id?: string;
}

// --- API Configuration ---
// Unified Deployment: Backend is served under /api on the same domain
const API_BASE = "/api";
const NGROK_HEADERS = {
  "ngrok-skip-browser-warning": "true",
  "Content-Type": "application/json"
};


export default function App() {
  const [view, setView] = useState<'input' | 'results' | 'pathway' | 'hospitals' | 'cost'>('input');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [availablePathways, setAvailablePathways] = useState<AvailablePathway[]>([]);
  
  const [pathwayLoading, setPathwayLoading] = useState(false);
  const [currentPathway, setCurrentPathway] = useState<PathwayResponse | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<'mild' | 'moderate' | 'severe'>('moderate');
  const [activePathwayId, setActivePathwayId] = useState<string | null>(null);

  const [cities, setCities] = useState<string[]>([]);
  const [selectedCity, setSelectedCity] = useState<string>('');
  const [hospitalsLoading, setHospitalsLoading] = useState(false);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [scoringWeights, setScoringWeights] = useState<ScoringWeights | null>(null);
  const [hospitalsCount, setHospitalsCount] = useState({ found: 0, showing: 0 });
  
  const [filterType, setFilterType] = useState<string>('All');
  const [filterNABH, setFilterNABH] = useState(false);
  const [showCitySelector, setShowCitySelector] = useState(false);

  const [costLoading, setCostLoading] = useState(false);
  const [costEstimate, setCostEstimate] = useState<CostEstimateResponse | null>(null);
  const [selectedHospitalType, setSelectedHospitalType] = useState<'government' | 'trust' | 'private' | 'corporate'>('private');
  const [hasInsurance, setHasInsurance] = useState(false);

  const examples = [
    "chest pain while walking",
    "knee pain, difficulty walking",
    "heartburn after meals"
  ];

  useEffect(() => {
    const fetchInitialData = async () => {
      // Default cities for Indian healthcare context as fallback
      const defaultCities = ["Bangalore", "Delhi", "Mumbai", "Chennai", "Hyderabad", "Pune", "Ahmedabad", "Kolkata"];
      
      try {
        // Fetch Pathways (Optional)
        try {
          const pathwayRes = await axios.get(`${API_BASE}/pathways`, { headers: NGROK_HEADERS });
          if (Array.isArray(pathwayRes.data)) {
            setAvailablePathways(pathwayRes.data);
          }
        } catch (e) {
          console.warn("Pathways discovery endpoint not found, skipping list.");
        }

        // Fetch Cities (Optional)
        try {
          const cityRes = await axios.get(`${API_BASE}/cities`, { headers: NGROK_HEADERS });
          if (cityRes.data?.cities && Array.isArray(cityRes.data.cities)) {
            setCities(cityRes.data.cities);
            setSelectedCity(cityRes.data.cities[0]);
          } else {
            setCities(defaultCities);
            setSelectedCity(defaultCities[0]);
          }
        } catch (e) {
          console.warn("Cities discovery endpoint not found, using default Indian cities.");
          setCities(defaultCities);
          setSelectedCity(defaultCities[0]);
        }
      } catch (err) {
        console.error("Unexpected error in background data fetching:", err);
      }
    };
    fetchInitialData();
  }, []);

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE}/analyze-query`, {
        query: query
      }, { headers: NGROK_HEADERS });

      setResult(response.data);
      setView('results');
    } catch (err) {
      console.error("API Error:", err);
      setError("The analysis server is currently unreachable. Please check your connection or try again later.");
    } finally {
      setLoading(false);
    }
  };

  const fetchPathwayData = async (pathwayId: string, severity: 'mild' | 'moderate' | 'severe') => {
    setPathwayLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE}/get-pathway`, {
        pathway_id: pathwayId,
        severity: severity
      }, { headers: NGROK_HEADERS });
      setCurrentPathway(response.data);
      setSelectedSeverity(severity);
      setActivePathwayId(pathwayId);
      setView('pathway');
    } catch (err) {
      console.error("Pathway API Error:", err);
      setError("Could not load pathway information.");
    } finally {
      setPathwayLoading(false);
    }
  };

  const handleLevelChange = (level: 'mild' | 'moderate' | 'severe') => {
    if (activePathwayId) {
      fetchPathwayData(activePathwayId, level);
    }
  };

  const fetchHospitals = async (pType?: string, pNABH?: boolean, pCity?: string) => {
    if (!activePathwayId) return;
    
    setHospitalsLoading(true);
    const currentFilterType = pType !== undefined ? pType : filterType;
    const currentFilterNABH = pNABH !== undefined ? pNABH : filterNABH;
    setFilterType(currentFilterType);
    setFilterNABH(currentFilterNABH);
    
    // Ensure targetCity matches exactly one of the valid strings (casing matters)
    const targetCity = pCity || selectedCity;
    setSelectedCity(targetCity);
    setError(null);

    try {
      // The payload must use strictly null for filter_type if no filter is active
      const response = await axios.post(`${API_BASE}/get-hospitals`, {
        pathway_id: activePathwayId, // condition.pathway_id (e.g. "pathway_angina")
        city: targetCity,
        top_n: 5,
        filter_type: (currentFilterType === 'All' || !currentFilterType) ? null : currentFilterType.toLowerCase(),
        filter_nabh: currentFilterNABH
      }, { headers: NGROK_HEADERS });
      
      const data: HospitalResponse = response.data;
      setHospitals(data.results);
      setScoringWeights(data.scoring_weights);
      setHospitalsCount({ found: data.total_found, showing: data.showing });
      setView('hospitals');
      setShowCitySelector(false);
    } catch (err) {
      console.error("Hospital API Error:", err);
      setError("City-specific hospital ranking failed. Please ensure the condition is supported in the chosen city.");
    } finally {
      setHospitalsLoading(false);
    }
  };

  const fetchCostEstimate = async (pType?: 'government' | 'trust' | 'private' | 'corporate', pInsurance?: boolean) => {
    if (!activePathwayId) return;

    setCostLoading(true);
    const targetType = pType || selectedHospitalType;
    const targetInsurance = pInsurance !== undefined ? pInsurance : hasInsurance;
    
    setSelectedHospitalType(targetType);
    setHasInsurance(targetInsurance);

    try {
      const response = await axios.post(`${API_BASE}/estimate-cost`, {
        pathway_id: activePathwayId,
        city: selectedCity,
        hospital_type: targetType,
        has_insurance: targetInsurance
      }, { headers: NGROK_HEADERS });

      setCostEstimate(response.data);
      setView('cost');
    } catch (err) {
      console.error("Cost Estimate API Error:", err);
      setError("Cost data unavailable for this condition or specific parameters.");
    } finally {
      setCostLoading(false);
    }
  };

  const handleReset = () => {
    setView('input');
    setResult(null);
    setError(null);
    setCurrentPathway(null);
    setActivePathwayId(null);
    setSelectedSeverity('moderate');
    setHospitals([]);
    setFilterType('All');
    setFilterNABH(false);
    setCostEstimate(null);
    setSelectedHospitalType('private');
    setHasInsurance(false);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.7) return 'bg-emerald-500';
    if (score >= 0.5) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const getBadgeColor = (type: string) => {
    switch(type.toLowerCase()) {
      case 'consultation': return 'bg-teal-500/10 text-teal-400 border-teal-500/20';
      case 'diagnostic': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'surgery': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'procedure': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'therapy': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'medication': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'lifestyle': return 'bg-lime-500/10 text-lime-400 border-lime-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const StepCard = ({ step, index, isBranch = false }: { step: PathwayStep, index: number, isBranch?: boolean }) => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08 }}
      className={`glass rounded-2xl p-5 mb-4 relative ${isBranch ? 'border-l-4 border-l-amber-500' : ''}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white leading-none">{step.name}</span>
          <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getBadgeColor(step.type)}`}>
            {step.type}
          </span>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${step.mandatory ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>
          {step.mandatory ? 'Mandatory' : 'Optional'}
        </span>
      </div>
      <p className="text-xs text-slate-400 mb-4 line-clamp-2">{step.description}</p>
      <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
        <div className="flex items-center gap-1.5 text-xs text-brand-teal font-semibold">
          <Activity size={12} />
          {step.cost_tier_info.label}
        </div>
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">
          Est. {step.cost_tier_info.range}
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="min-h-screen font-sans selection:bg-brand-teal/30 medical-gradient relative overflow-x-hidden">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4 border-b border-white/5 bg-brand-navy/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div 
            className="flex items-center gap-2 cursor-pointer group"
            onClick={handleReset}
          >
            <div className="p-2 rounded-xl bg-brand-teal/10 text-brand-teal group-hover:bg-brand-teal/20 transition-colors">
              <Stethoscope size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              Arogya<span className="text-brand-teal">Path</span>
            </h1>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-slate-400 font-medium">
            <span className="hover:text-brand-teal cursor-pointer transition-colors">How it works</span>
            <span className="hover:text-brand-teal cursor-pointer transition-colors">Data Privacy</span>
            <button className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white transition-all">
              TenzorX 2026
            </button>
          </div>
        </div>
      </header>

      <main className="pt-24 pb-20 px-6">
        <div className="max-w-4xl mx-auto">
          <AnimatePresence mode="wait">
            {view === 'input' ? (
              <motion.div
                key="input-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex flex-col items-center text-center py-12 md:py-20"
              >
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.2 }}
                  className="mb-8 p-4 rounded-3xl bg-brand-teal/10 text-brand-teal ring-1 ring-brand-teal/20 shadow-[0_0_40px_-15px_rgba(14,165,233,0.5)]"
                >
                  <Activity size={48} />
                </motion.div>

                <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 tracking-tight leading-tight">
                  Decision Intelligence for <br/>
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-teal to-blue-400">
                    Indian Healthcare
                  </span>
                </h2>
                
                <p className="text-slate-400 text-lg md:text-xl max-w-2xl mb-12 leading-relaxed">
                  Navigate clinical pathways with ease. Describe your symptoms in plain English 
                  and get instant clinical insights, hospital matches, and cost estimations.
                </p>

                <form 
                  onSubmit={handleAnalyze}
                  className="w-full max-w-2xl glass rounded-3xl p-2 relative group focus-within:ring-2 focus-within:ring-brand-teal/50 transition-all duration-300"
                >
                  <textarea
                    className="w-full bg-transparent border-none focus:ring-0 px-6 py-6 text-xl text-white placeholder-slate-500 resize-none min-h-[140px]"
                    placeholder="Describe your symptoms (e.g., chest pain while walking...)"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAnalyze();
                      }
                    }}
                  />
                  
                  <div className="flex items-center justify-between px-4 pb-4">
                    <div className="flex flex-wrap gap-2">
                      {examples.map((ex, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setQuery(ex)}
                          className="text-xs px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 text-slate-400 hover:text-white transition-all"
                        >
                          "{ex}"
                        </button>
                      ))}
                    </div>
                    <button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="px-6 py-3 rounded-2xl bg-brand-teal text-brand-navy font-bold flex items-center gap-2 hover:bg-white transition-all disabled:opacity-50 disabled:cursor-not-allowed group shadow-[0_0_20px_-5px_rgba(14,165,233,0.5)]"
                    >
                      {loading ? (
                        <RotateCcw className="animate-spin" size={20} />
                      ) : (
                        <>
                          Analyze
                          <ChevronRight size={20} className="group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {error && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-8 flex items-center gap-3 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400"
                  >
                    <AlertCircle size={20} />
                    <span className="text-sm font-medium">{error}</span>
                  </motion.div>
                )}
              </motion.div>
            ) : view === 'results' ? (
              <motion.div
                key="results-view"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-8"
              >
                {/* Results Header */}
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-white/5">
                  <div>
                    <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-widest mb-2">Original Inquiry</h3>
                    <p className="text-2xl text-white font-medium italic">"{result?.query}"</p>
                  </div>
                  <button 
                    onClick={handleReset}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all font-medium"
                  >
                    <RotateCcw size={18} />
                    New Search
                  </button>
                </div>

                {/* Notifications */}
                <div className="space-y-4">
                  {result?.emergency_flag && (
                    <motion.div 
                      initial={{ scale: 0.95, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="bg-rose-600 rounded-3xl p-6 md:p-8 flex flex-col md:flex-row items-center gap-6 shadow-[0_0_50px_-10px_rgba(239,68,68,0.4)]"
                    >
                      <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center animate-pulse">
                        <AlertCircle size={40} className="text-white" />
                      </div>
                      <div className="flex-1 text-center md:text-left">
                        <h4 className="text-2xl font-bold text-white mb-2">CRITICAL EMERGENCY DETECTED</h4>
                        <p className="text-white/90 text-lg">{result.emergency_message}</p>
                      </div>
                      <button 
                        onClick={() => window.open('tel:112')}
                        className="w-full md:w-auto px-10 py-5 rounded-2xl bg-white text-rose-600 text-xl font-extrabold flex items-center justify-center gap-3 hover:scale-105 transition-transform"
                      >
                        <PhoneCall size={28} />
                        CALL 112
                      </button>
                    </motion.div>
                  )}

                  {result?.low_confidence && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5 flex items-start gap-4">
                      <AlertTriangle className="text-amber-500 shrink-0" size={24} />
                      <div>
                        <h5 className="text-amber-500 font-bold mb-1">Incomplete Data Profile</h5>
                        <p className="text-amber-200/70 text-sm">We need more details — please describe your symptoms more specifically for a precise diagnosis.</p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                  {/* Left Column: Condition Results */}
                  <div className="lg:col-span-2 space-y-6">
                    <h3 className="text-xl font-bold text-white flex items-center gap-3">
                      Clinical Candidates
                      <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-slate-400 font-normal">
                        ICD-10 Mapped
                      </span>
                    </h3>

                    <div className="space-y-4">
                      {result?.conditions.map((condition, idx) => (
                        <motion.div
                          key={condition.id}
                          initial={{ x: -20, opacity: 0 }}
                          animate={{ x: 0, opacity: 1 }}
                          transition={{ delay: idx * 0.1 }}
                          className={`glass p-6 rounded-3xl relative overflow-hidden group hover:ring-1 hover:ring-brand-teal/30 transition-all ${idx === 0 ? 'ring-1 ring-brand-teal/40 bg-brand-teal/[0.03]' : ''}`}
                        >
                          {idx === 0 && (
                            <div className="absolute top-0 right-0 px-4 py-1 bg-brand-teal text-brand-navy text-[10px] font-black uppercase tracking-widest rounded-bl-xl">
                              Likely Condition
                            </div>
                          )}
                          
                          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className={`text-xl font-bold ${idx === 0 ? 'text-white' : 'text-slate-200'}`}>
                                  {condition.name}
                                </h4>
                                <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] font-mono text-slate-400 uppercase">
                                  {condition.icd10}
                                </span>
                              </div>
                              <p className="text-xs text-slate-500 font-medium tracking-tight">PATHWAY REF: {condition.pathway_id}</p>
                            </div>
                            <div className="text-right">
                              <span className={`text-2xl font-black ${idx === 0 ? 'text-brand-teal' : 'text-slate-400'}`}>
                                {Math.round(condition.confidence * 100)}%
                              </span>
                              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Confidence Score</div>
                            </div>
                          </div>

                          <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mb-4">
                            <motion.div 
                              initial={{ width: 0 }}
                              animate={{ width: `${condition.confidence * 100}%` }}
                              transition={{ duration: 1, delay: 0.5 + (idx * 0.1) }}
                              className={`h-full ${getConfidenceColor(condition.confidence)}`}
                            />
                          </div>

                          <button 
                            onClick={() => fetchPathwayData(condition.pathway_id, 'moderate')}
                            disabled={pathwayLoading}
                            className="w-full py-3 rounded-xl bg-white/[0.03] border border-white/5 text-slate-300 font-bold text-xs flex items-center justify-center gap-2 hover:bg-brand-teal hover:text-brand-navy transition-all group/btn"
                          >
                            {pathwayLoading ? (
                              <RotateCcw className="animate-spin" size={14} />
                            ) : (
                              <>
                                View Treatment Pathway
                                <ChevronRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                              </>
                            )}
                          </button>
                        </motion.div>
                      ))}
                    </div>

                    {/* All Pathways List Section Section Added here */}
                    {availablePathways.length > 0 && (
                      <div className="mt-12 bg-white/[0.02] border border-white/5 p-6 rounded-3xl">
                        <h4 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                          <LayoutGrid size={16} />
                          Also available for other conditions:
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {availablePathways.map((path) => (
                            <button
                              key={path.id}
                              onClick={() => fetchPathwayData(path.pathway_id || path.id, 'moderate')}
                              className="text-left p-4 rounded-2xl bg-white/5 border border-white/5 hover:border-brand-teal/30 transition-all flex items-center justify-between group"
                            >
                              <div className="flex-1 min-w-0 pr-4">
                                <div className="text-sm font-bold text-white group-hover:text-brand-teal transition-colors truncate">{path.name}</div>
                                <div className="text-[10px] text-slate-500 uppercase font-bold tracking-tight">{path.category}</div>
                              </div>
                              <ArrowLeft size={16} className="text-slate-600 group-hover:text-brand-teal rotate-180 transition-all shrink-0" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Semantics Information */}
                  <div className="space-y-6">
                    <div className="glass rounded-3xl p-6">
                      <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-emerald-500" />
                        Symptoms Extracted
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {result?.extracted_symptoms.map((symptom, i) => (
                          <span key={i} className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
                            {symptom}
                          </span>
                        ))}
                        {(!result?.extracted_symptoms || result.extracted_symptoms.length === 0) && (
                          <span className="text-slate-500 text-sm italic">None identified</span>
                        )}
                      </div>
                    </div>

                    <div className="glass rounded-3xl p-6">
                      <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <XCircle size={16} className="text-slate-500" />
                        Negations
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {result?.negated_symptoms.map((symptom, i) => (
                          <span key={i} className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-slate-500 text-sm font-medium line-through decoration-slate-600">
                            {symptom}
                          </span>
                        ))}
                        {(!result?.negated_symptoms || result.negated_symptoms.length === 0) && (
                          <span className="text-slate-500 text-sm italic">None identified</span>
                        )}
                      </div>
                    </div>

                    <div className="p-6 rounded-3xl bg-brand-teal/5 border border-brand-teal/10">
                      <div className="flex items-start gap-4">
                        <Info size={20} className="text-brand-teal shrink-0 mt-1" />
                        <div>
                          <h4 className="text-white font-bold text-sm mb-1">Clinical Note</h4>
                          <p className="text-slate-400 text-xs leading-relaxed">
                            These results are derived from large-scale medical embedding models and standard ICD-10 coding sets. Confidence thresholds vary by patient intent specificity.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : view === 'cost' ? (
              <motion.div
                key="cost-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="space-y-8"
              >
                {/* Cost Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-white/5">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setView('hospitals')}
                      className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all"
                    >
                      <ArrowLeft size={20} />
                    </button>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h2 className="text-2xl font-bold text-white">Cost Estimate: {costEstimate?.condition_name}</h2>
                        <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-xs font-mono text-brand-teal uppercase font-bold">
                          {costEstimate?.icd10}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">
                        {costEstimate?.city} · {selectedHospitalType.charAt(0).toUpperCase() + selectedHospitalType.slice(1)} · {(costEstimate?.city_tier || '').toUpperCase()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Hospital Type Selector & Insurance Toggle */}
                <div className="flex flex-col md:flex-row gap-6 items-start md:items-center">
                  <div className="flex flex-wrap p-1.5 gap-1 rounded-2xl bg-white/5 border border-white/5">
                    {(['government', 'trust', 'private', 'corporate'] as const).map((type) => (
                      <button
                        key={type}
                        disabled={costLoading}
                        onClick={() => fetchCostEstimate(type)}
                        className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center gap-2 ${
                          selectedHospitalType === type 
                            ? 'bg-brand-teal text-brand-navy shadow-[0_0_15px_-5px_rgba(14,165,233,0.5)]'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                        }`}
                      >
                        <span>{type === 'government' ? '🏛️' : type === 'trust' ? '🏥' : type === 'private' ? '🏢' : '🏙️'}</span>
                        {type}
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-4 px-5 py-2.5 rounded-2xl bg-white/5 border border-white/5 hover:border-brand-teal/30 transition-all">
                    <div className="p-1.5 rounded-lg bg-brand-teal/10 text-brand-teal">
                      <ShieldCheck size={18} />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Smart Coverage</span>
                      <span className="text-xs font-bold text-white leading-tight">PM-JAY / Insurance</span>
                    </div>
                    <button 
                      onClick={() => fetchCostEstimate(selectedHospitalType, !hasInsurance)}
                      disabled={costLoading}
                      className={`w-10 h-5 rounded-full relative transition-all ml-2 ${hasInsurance ? 'bg-brand-teal' : 'bg-white/10'}`}
                    >
                      <motion.div 
                        animate={{ x: hasInsurance ? 20 : 2 }}
                        className="absolute top-1 left-0 w-3 h-3 rounded-full bg-white shadow-sm" 
                      />
                    </button>
                  </div>
                </div>

                {/* Loading State Overlay */}
                {costLoading && (
                  <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-4 glass rounded-3xl">
                    <RotateCcw size={40} className="animate-spin text-brand-teal" />
                    <p className="font-bold uppercase tracking-widest text-xs">Computing Treatment Costs...</p>
                  </div>
                )}

                {!costLoading && costEstimate && (
                  <div className="space-y-8">
                    {/* Total Cost Banners */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <motion.div 
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="p-8 rounded-[2.5rem] bg-gradient-to-br from-brand-teal/20 via-brand-teal/5 to-transparent border border-brand-teal/20 shadow-[0_0_50px_-20px_rgba(14,165,233,0.3)] relative overflow-hidden group"
                      >
                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform">
                          <Coins size={80} />
                        </div>
                        <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                          💰 Estimated Total Cost
                        </h4>
                        <div className="text-4xl md:text-5xl font-black text-white mb-2 italic">
                          {costEstimate.total_range_label}
                        </div>
                        <p className="text-slate-500 text-sm font-medium">Standard pricing without insurance</p>
                      </motion.div>

                      {hasInsurance && costEstimate.insurance.eligible && (
                        <motion.div 
                          initial={{ scale: 0.95, opacity: 0, x: 20 }}
                          animate={{ scale: 1, opacity: 1, x: 0 }}
                          className="p-8 rounded-[2.5rem] bg-gradient-to-br from-emerald-500/20 via-emerald-500/5 to-transparent border border-emerald-500/20 shadow-[0_0_50px_-20px_rgba(16,185,129,0.3)] relative overflow-hidden group"
                        >
                          <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform">
                            <ShieldCheck size={80} />
                          </div>
                          <h4 className="text-sm font-black text-emerald-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                            🛡️ After {costEstimate.insurance.scheme} Coverage
                          </h4>
                          <div className="text-4xl md:text-5xl font-black text-white mb-2 italic">
                            ₹{costEstimate.insurance.out_of_pocket_min.toLocaleString()} – ₹{costEstimate.insurance.out_of_pocket_max.toLocaleString()}
                          </div>
                          <p className="text-emerald-500/70 text-sm font-medium italic">
                            Out-of-pocket · {costEstimate.insurance.scheme} covers ₹{costEstimate.insurance.covered_amount.toLocaleString()}
                          </p>
                        </motion.div>
                      )}
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                      {/* Cost Breakdown List */}
                      <div className="lg:col-span-2 space-y-3">
                        <h3 className="text-lg font-bold text-white flex items-center gap-3 mb-6">
                          Cost Breakdown
                          <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-slate-500 font-black uppercase tracking-tighter">
                            By Component
                          </span>
                        </h3>
                        {costEstimate.breakdown.map((item, idx) => {
                          const getIcon = (comp: string) => {
                            switch(comp.toLowerCase()) {
                              case 'consultation': return '🩺';
                              case 'diagnostics': return '🔬';
                              case 'procedure': return '🏥';
                              case 'stay': return '🛏️';
                              case 'medicines': return '💊';
                              case 'contingency': return '🔄';
                              default: return '📍';
                            }
                          };

                          if (item.min === 0 && item.max === 0) {
                            return (
                              <motion.div
                                key={idx}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                className="glass p-4 rounded-2xl flex items-center justify-between opacity-50 grayscale"
                              >
                                <div className="flex items-center gap-4">
                                  <span className="text-2xl">{getIcon(item.component)}</span>
                                  <span className="text-sm font-bold text-slate-400">{item.label}</span>
                                </div>
                                <span className="px-3 py-1 rounded-lg bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-600">Not Required</span>
                              </motion.div>
                            );
                          }

                          return (
                            <motion.div
                              key={idx}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: idx * 0.05 }}
                              className="glass p-5 rounded-3xl flex items-center justify-between hover:ring-1 hover:ring-brand-teal/30 transition-all group"
                            >
                              <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-2xl group-hover:bg-brand-teal/10 transition-colors">
                                  {getIcon(item.component)}
                                </div>
                                <div>
                                  <h5 className="font-bold text-white mb-0.5">{item.label}</h5>
                                  <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">{item.component}</span>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-black text-white italic group-hover:text-brand-teal transition-colors">
                                  ₹{item.min.toLocaleString()} – ₹{item.max.toLocaleString()}
                                </div>
                              </div>
                            </motion.div>
                          );
                        })}
                      </div>

                      {/* Visual & Calc Sidebar */}
                      <div className="space-y-6">
                        <div className="glass rounded-[2rem] p-6">
                          <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <TrendingUp size={16} />
                            Cost Distribution
                          </h4>
                          
                          {/* Proportional Cost Chart */}
                          <div className="h-10 w-full flex bg-white/5 rounded-2xl overflow-hidden mb-6 p-1">
                            {costEstimate.breakdown.map((item, idx) => {
                              const colors: any = {
                                consultation: 'bg-teal-500',
                                diagnostics: 'bg-blue-500',
                                procedure: 'bg-rose-500',
                                stay: 'bg-purple-500',
                                medicines: 'bg-emerald-500',
                                contingency: 'bg-slate-500'
                              };
                              const percentage = (item.max / costEstimate.total_max) * 100;
                              if (percentage === 0) return null;
                              return (
                                <motion.div 
                                  key={idx}
                                  initial={{ width: 0 }}
                                  animate={{ width: `${percentage}%` }}
                                  className={`${colors[item.component] || 'bg-slate-500'} h-full transition-all cursor-help relative group/chart`}
                                  title={`${item.label}: ${Math.round(percentage)}%`}
                                >
                                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover/chart:block z-50">
                                    <div className="bg-brand-navy p-2 rounded-lg border border-white/10 text-[10px] font-bold text-white whitespace-nowrap shadow-xl">
                                      {item.label} ({Math.round(percentage)}%)
                                    </div>
                                  </div>
                                </motion.div>
                              );
                            })}
                          </div>

                          <div className="space-y-4">
                            <details className="group">
                              <summary className="flex items-center justify-between cursor-pointer list-none list-inside">
                                <h5 className="text-xs font-bold text-slate-300 flex items-center gap-2">
                                  <Info size={14} className="text-brand-teal" />
                                  How was this calculated?
                                </h5>
                                <ChevronRight size={14} className="text-slate-600 group-open:rotate-90 transition-transform" />
                              </summary>
                              <div className="mt-4 p-4 rounded-2xl bg-white/[0.03] space-y-3">
                                <div className="flex justify-between text-[11px]">
                                  <span className="text-slate-500">City Tier: {(costEstimate.city_tier || '').toUpperCase()}</span>
                                  <span className="text-white font-bold">×{costEstimate.city_tier === 'tier1' ? '1.5' : costEstimate.city_tier === 'tier2' ? '1.2' : '1.0'}</span>
                                </div>
                                <div className="flex justify-between text-[11px]">
                                  <span className="text-slate-500">Hospital: {selectedHospitalType.charAt(0).toUpperCase() + selectedHospitalType.slice(1)}</span>
                                  <span className="text-white font-bold">×{selectedHospitalType === 'private' ? '1.8' : selectedHospitalType === 'corporate' ? '2.2' : selectedHospitalType === 'trust' ? '1.3' : '0.9'}</span>
                                </div>
                                <div className="pt-2 border-t border-white/5 flex justify-between text-xs">
                                  <span className="font-bold text-slate-300">Combined Multiplier</span>
                                  <span className="font-black text-brand-teal">×{costEstimate.combined_multiplier}</span>
                                </div>
                                <p className="text-[9px] text-slate-600 italic mt-2 leading-relaxed">
                                  Base rates derived from CGHS / NHP secondary care data sets (2024-25 Revision).
                                </p>
                              </div>
                            </details>
                          </div>
                        </div>

                        {costEstimate.notes && (
                          <div className="p-6 rounded-3xl bg-amber-500/5 border border-amber-500/10">
                            <div className="flex items-start gap-4">
                              <AlertTriangle size={20} className="text-amber-500 shrink-0 mt-1" />
                              <div className="space-y-2">
                                <h4 className="text-amber-500 font-bold text-sm uppercase tracking-tight">Clinical Insights</h4>
                                <p className="text-amber-200/60 text-xs leading-relaxed italic">
                                  {costEstimate.notes}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        <p className="text-[10px] text-slate-600 text-center italic px-4 leading-normal">
                          {costEstimate.disclaimer}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            ) : view === 'hospitals' ? (
              <motion.div
                key="hospitals-view"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.05 }}
                className="space-y-8"
              >
                {/* Hospitals Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-white/5">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setView('pathway')}
                      className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all"
                    >
                      <ArrowLeft size={20} />
                    </button>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h2 className="text-2xl font-bold text-white">Hospitals for {currentPathway?.condition}</h2>
                        <button 
                          onClick={() => setShowCitySelector(!showCitySelector)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-brand-teal/10 border border-brand-teal/20 text-brand-teal text-[10px] font-black uppercase tracking-widest hover:bg-brand-teal/20 transition-all"
                        >
                          📍 {selectedCity}
                          <Search size={10} />
                        </button>
                      </div>
                      <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">
                        Ranked by: Rating 35% · Distance 30% · Type 20% · NABH 15%
                      </p>
                    </div>
                  </div>
                </div>

                {/* City Selector Popup */}
                <AnimatePresence>
                  {showCitySelector && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="glass rounded-3xl p-6 flex flex-wrap gap-2"
                    >
                      {cities.map(city => (
                        <button
                          key={city}
                          onClick={() => fetchHospitals(filterType, filterNABH, city)}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${selectedCity === city ? 'bg-brand-teal text-brand-navy shadow-[0_0_15px_-5px_rgba(14,165,233,0.5)]' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
                        >
                          {city}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Filter Bar */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex flex-wrap gap-2">
                    {['All', 'Government', 'Private', 'Corporate'].map((type) => (
                      <button
                        key={type}
                        onClick={() => fetchHospitals(type)}
                        className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${filterType === type ? 'bg-brand-teal text-brand-navy' : 'bg-white/5 text-slate-500 hover:bg-white/10'}`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-3 px-4 py-2 rounded-2xl bg-white/5 border border-white/5">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">NABH Only</span>
                    <button 
                      onClick={() => fetchHospitals(filterType, !filterNABH)}
                      className={`w-10 h-5 rounded-full relative transition-all ${filterNABH ? 'bg-brand-teal' : 'bg-white/10'}`}
                    >
                      <motion.div 
                        animate={{ x: filterNABH ? 20 : 2 }}
                        className="absolute top-1 left-0 w-3 h-3 rounded-full bg-white shadow-sm" 
                      />
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-bold text-slate-600 mb-2">
                  <span>Found {hospitalsCount.found} hospitals</span>
                  <span className="w-1 h-1 rounded-full bg-slate-800"></span>
                  <span>Showing top {hospitalsCount.showing}</span>
                </div>

                {/* Hospital Rankings List */}
                <div className="space-y-4">
                  {hospitalsLoading ? (
                    <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-4">
                      <RotateCcw size={40} className="animate-spin text-brand-teal" />
                      <p className="font-bold uppercase tracking-widest text-xs">Computing Optimal Providers...</p>
                    </div>
                  ) : hospitals.length > 0 ? (
                    hospitals.map((hospital, idx) => (
                      <motion.div
                        key={hospital.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.08 }}
                        className="glass p-6 md:p-8 rounded-[2rem] relative overflow-hidden group hover:ring-1 hover:ring-brand-teal/30 transition-all"
                      >
                        {/* Rank Badge */}
                        <div className="absolute top-0 left-0 px-6 py-2 bg-white/10 text-white font-black italic rounded-br-2xl text-xl">
                          #{idx + 1}
                        </div>

                        {/* PM-JAY Badge */}
                        {hospital.pm_jay_eligible && (
                          <div className="absolute top-0 right-0 px-4 py-1.5 bg-blue-600 text-white text-[10px] font-black uppercase tracking-widest rounded-bl-xl flex items-center gap-1.5">
                            🏛️ PM-JAY Eligible
                          </div>
                        )}

                        <div className="flex flex-col md:flex-row justify-between gap-6 mb-8 mt-6">
                          <div className="flex-1">
                            <div className="flex items-start gap-3 mb-2">
                              <h4 className="text-2xl font-bold text-white group-hover:text-brand-teal transition-colors">
                                {hospital.name}
                              </h4>
                              {hospital.nabh_accredited && (
                                <span className="mt-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase flex items-center gap-1">
                                  NABH ✓
                                </span>
                              )}
                            </div>
                            
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-400 mb-4">
                              <div className="flex items-center gap-1 text-amber-500 font-bold">
                                <span>⭐ {hospital.rating}</span>
                                <span className="text-[10px] text-slate-500 font-normal uppercase">({hospital.review_count.toLocaleString()})</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <span className="text-slate-600">📍</span>
                                {hospital.distance_km} km
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="capitalize">{hospital.type_label}</span>
                                <span className="w-1 h-1 rounded-full bg-slate-700"></span>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                                  hospital.cost_category === 'budget' ? 'bg-emerald-500/10 text-emerald-400' :
                                  hospital.cost_category === 'mid' ? 'bg-amber-500/10 text-amber-400' :
                                  'bg-rose-500/10 text-rose-400'
                                }`}>
                                  {hospital.cost_category === 'budget' ? '₹ Budget' :
                                   hospital.cost_category === 'mid' ? '₹₹ Mid-range' :
                                   '₹₹₹ Premium'}
                                </span>
                              </div>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              {hospital.tradeoff_tags.map((tag, i) => (
                                <span key={i} className="px-3 py-1 rounded-xl bg-white/5 border border-white/5 text-slate-400 text-xs font-semibold flex items-center gap-1.5">
                                  <span>{tag.icon}</span>
                                  {tag.label}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="md:w-64 text-right">
                            <div className="mb-2">
                              <span className="text-3xl font-black text-white italic">
                                {Math.round(hospital.final_score * 100)}%
                              </span>
                              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Recommendation Score</div>
                            </div>
                            
                            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden mb-3">
                              <div 
                                className={`h-full ${hospital.final_score > 0.75 ? 'bg-emerald-500' : hospital.final_score > 0.5 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                style={{ width: `${hospital.final_score * 100}%` }}
                              />
                            </div>

                            <div className="flex gap-0.5 h-1">
                              <div className="flex-1 bg-emerald-500/40 rounded-full" style={{ opacity: hospital.score_breakdown.rating_score }} />
                              <div className="flex-1 bg-blue-500/40 rounded-full" style={{ opacity: hospital.score_breakdown.distance_score }} />
                              <div className="flex-1 bg-white/20 rounded-full" style={{ opacity: hospital.score_breakdown.type_score }} />
                              <div className="flex-1 bg-brand-teal rounded-full" style={{ opacity: hospital.score_breakdown.nabh_bonus }} />
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-white/5 overflow-x-auto">
                          <div className="flex items-center gap-2 text-slate-500">
                            <span className="text-lg">🛏</span>
                            <span className="text-xs font-bold text-slate-300">{hospital.bed_count} Beds</span>
                          </div>
                          {hospital.emergency && (
                            <div className="flex items-center gap-2 text-rose-400">
                              <span className="text-lg">🚨</span>
                              <span className="text-xs font-bold">Emergency</span>
                            </div>
                          )}
                          {hospital.icu_available && (
                            <div className="flex items-center gap-2 text-brand-teal">
                              <span className="text-lg">🏥</span>
                              <span className="text-xs font-bold">ICU Ready</span>
                            </div>
                          )}
                          <div className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors cursor-pointer">
                            <PhoneCall size={14} />
                            <span className="text-xs font-bold truncate">{hospital.phone}</span>
                          </div>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="py-20 text-center glass rounded-3xl">
                      <p className="text-slate-500 font-bold uppercase tracking-widest text-sm">No hospitals found — try removing filters.</p>
                    </div>
                  )}
                </div>

                {/* Estimate Cost CTA - Moved to Bottom */}
                <div className="flex justify-center pt-12">
                  <button
                    onClick={() => fetchCostEstimate()}
                    disabled={costLoading}
                    className="w-full md:w-auto px-10 py-5 rounded-3xl bg-brand-teal text-brand-navy font-extrabold flex items-center justify-center gap-3 hover:bg-white transition-all shadow-[0_0_30px_-5px_rgba(14,165,233,0.6)] group"
                  >
                    {costLoading ? (
                      <RotateCcw className="animate-spin" size={24} />
                    ) : (
                      <>
                        <span className="text-2xl">💰</span>
                        Estimate Cost
                        <ChevronRight size={24} className="group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="pathway-view"
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                className="space-y-8"
              >
                {/* Pathway Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-white/5">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setView('results')}
                      className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-all"
                    >
                      <ArrowLeft size={20} />
                    </button>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="text-2xl font-bold text-white">{currentPathway?.condition}</h2>
                        <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-xs font-mono text-brand-teal uppercase font-bold">
                          {currentPathway?.icd10}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 uppercase font-black tracking-widest">Clinical Care Pathway - Tier 1 Protocols</p>
                    </div>
                  </div>

                  {/* Severity Selector Section */}
                  <div className="flex p-1.5 gap-1 rounded-2xl bg-white/5 border border-white/5">
                    {(['mild', 'moderate', 'severe'] as const).map((level) => (
                      <button
                        key={level}
                        disabled={pathwayLoading}
                        onClick={() => handleLevelChange(level)}
                        className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all ${
                          selectedSeverity === level 
                            ? level === 'mild' ? 'bg-emerald-500 text-brand-navy shadow-[0_0_15px_-5px_rgba(16,185,129,0.5)]'
                              : level === 'moderate' ? 'bg-amber-500 text-brand-navy shadow-[0_0_15px_-5px_rgba(245,158,11,0.5)]'
                              : 'bg-rose-500 text-white shadow-[0_0_15px_-5px_rgba(239,68,68,0.5)]'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                        }`}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Surgery Alert Banner Section */}
                {currentPathway?.has_surgery && (
                  <motion.div 
                    initial={{ scale: 0.98, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="bg-rose-500/10 border border-rose-500/20 p-5 rounded-3xl flex items-start gap-4"
                  >
                    <div className="p-3 rounded-2xl bg-rose-500/20 text-rose-500">
                      <HeartPulse size={24} />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-rose-500 font-bold mb-1 uppercase tracking-tight flex items-center gap-2">
                        ⚕️ This pathway may involve surgery
                      </h4>
                      <p className="text-rose-200/60 text-sm leading-relaxed">
                        Costs and recovery time vary significantly. Integrated costs reflect institutional averages; pre-surgical evaluations may incur additional diagnostics.
                      </p>
                    </div>
                  </motion.div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                  {/* Pathway Timeline Section */}
                  <div className="lg:col-span-3">
                    <div className="relative pl-8 md:pl-10 space-y-2">
                      {/* Timeline Connector Line */}
                      <div className="absolute left-3.5 md:left-4.5 top-2 bottom-6 w-0.5 bg-gradient-to-b from-brand-teal via-brand-teal/50 to-transparent" />
                      
                      {pathwayLoading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-slate-500 gap-4">
                          <RotateCcw size={40} className="animate-spin text-brand-teal" />
                          <p className="font-bold uppercase tracking-widest text-xs">Recalibrating Care Steps...</p>
                        </div>
                      ) : (
                        <>
                          <div className="mb-8">
                            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-3">
                              <span className="w-8 h-8 rounded-full bg-brand-teal flex items-center justify-center text-brand-navy text-sm font-black italic">B</span>
                              Base Protocol Steps
                            </h3>
                            {currentPathway?.base_steps.map((step, idx) => (
                              <div key={step.id} className="relative group">
                                {/* Step Circle */}
                                <div className="absolute -left-8 md:-left-10 top-6 w-7 h-7 md:w-9 md:h-9 rounded-full bg-brand-navy border-4 border-brand-teal flex items-center justify-center z-10 group-hover:scale-110 transition-transform">
                                  <span className="text-xs md:text-sm font-black text-white">{idx + 1}</span>
                                </div>
                                <StepCard step={step} index={idx} />
                              </div>
                            ))}
                          </div>

                          {currentPathway?.resolved_branch && (
                            <div className="mt-12 bg-white/[0.01] rounded-3xl p-6 border border-white/5">
                              <div className="relative mb-8">
                                <h3 className="text-white font-bold text-lg flex items-center gap-3">
                                  Based on severity — your pathway branches here:
                                </h3>
                              </div>
                              
                              <div className="inline-block px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500 font-black text-xs uppercase tracking-widest mb-8">
                                {currentPathway.resolved_branch.label}
                              </div>
                              
                              <div className="space-y-4">
                                {currentPathway.resolved_branch.steps.map((step, bIdx) => (
                                  <div key={step.id} className="relative group">
                                    <div className="absolute -left-14 top-6 w-7 h-7 md:w-9 md:h-9 rounded-full bg-brand-navy border-4 border-amber-500 flex items-center justify-center z-10">
                                      <span className="text-xs md:text-sm font-black text-white">{currentPathway.base_steps.length + bIdx + 1}</span>
                                    </div>
                                    <StepCard step={step} index={bIdx} isBranch={true} />
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Sidebar Stats Summary Counters Section */}
                  <div className="space-y-6">
                    <div className="glass rounded-3xl overflow-hidden">
                      <div className="p-6 bg-white/5 border-b border-white/5">
                        <h4 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-1">Resource Summary</h4>
                        <p className="text-lg font-bold text-white leading-tight">Care Intensity: {selectedSeverity}</p>
                      </div>
                      <div className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                            <span className="text-lg">✅</span>
                            Must-do steps
                          </div>
                          <span className="text-white font-black text-sm">{currentPathway?.mandatory_steps.length || 0}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-slate-400 text-xs font-bold">
                            <span className="text-lg">⚙️</span>
                            Optional steps
                          </div>
                          <span className="text-white font-black text-sm">{currentPathway?.optional_steps.length || 0}</span>
                        </div>
                        <div className="pt-4 border-t border-white/5 space-y-2">
                          <div className="text-[10px] uppercase font-black text-slate-600 tracking-tighter">Est. Recovery Window</div>
                          <div className="flex items-center gap-2 text-brand-teal font-bold">
                            <Clock size={16} />
                            {selectedSeverity === 'mild' ? '2-3 Weeks' : selectedSeverity === 'moderate' ? '4-8 Weeks' : '3-6 Months'}
                          </div>
                        </div>
                      </div>
                    </div>

                    <button 
                      onClick={() => fetchHospitals()}
                      disabled={hospitalsLoading}
                      className="w-full py-4 rounded-3xl bg-brand-teal text-brand-navy font-black flex items-center justify-center gap-2 hover:bg-white transition-all shadow-[0_0_20px_-5px_rgba(14,165,233,0.4)]"
                    >
                      {hospitalsLoading ? (
                        <RotateCcw className="animate-spin" size={20} />
                      ) : (
                        <>
                          🏥 Find Hospitals
                          <ChevronRight size={20} />
                        </>
                      )}
                    </button>

                    <div className="glass rounded-3xl p-6 bg-gradient-to-br from-brand-teal/10 to-transparent">
                      <h4 className="text-xs font-black text-white uppercase tracking-widest mb-4">Financial Support</h4>
                      <p className="text-[10px] text-slate-400 leading-relaxed mb-4">
                        This clinical path is integrated with standard insurance codes (PMJAY / CGHS). Contact our helpdesk for TPA assistance.
                      </p>
                      <button className="w-full py-3 rounded-xl bg-brand-teal/20 hover:bg-brand-teal/30 border border-brand-teal/30 text-brand-teal text-[10px] font-black uppercase tracking-widest transition-all">
                        Pre-Auth Assistance
                      </button>
                    </div>

                    <p className="text-[9px] text-slate-600 leading-normal px-2 italic">
                      Disclaimer: Protocol generated for educational navigation. Real-world decisions require synchronous clinician validation.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      <footer className="mt-auto px-6 py-10 border-t border-white/5">
        <div className="max-w-6xl mx-auto flex flex-col items-center gap-4 text-center">
          <div className="flex items-center gap-4 text-slate-500 mb-2">
            <span className="text-xs font-semibold tracking-widest uppercase">Verified Algorithms</span>
            <span className="w-1 h-1 rounded-full bg-slate-700"></span>
            <span className="text-xs font-semibold tracking-widest uppercase">Encryption Secured</span>
          </div>
          <p className="text-[10px] leading-relaxed text-slate-500 max-w-xl">
            <strong>Disclaimer:</strong> ArogyaPath is a decision support tool powered by AI for the TenzorX 2026 Hackathon. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health providers with any questions you may have regarding a medical condition. 
          </p>
          <p className="text-[10px] text-slate-600 mt-2">© 2026 ArogyaPath Systems. Part of the National AI Health Initiative.</p>
        </div>
      </footer>
    </div>
  );
}


