import React, { useState, useEffect } from 'react';
import { FeeRecord, FacultyMember, TimetableEntry, ExamEntry } from '../types';
import { api } from '../services/api';
import { DollarSign, Users, Calendar, Clock, BookOpen, CheckCircle, Search, ShieldCheck } from 'lucide-react';

export const AcademicView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'fees' | 'faculty' | 'timetable' | 'exams'>('fees');
  const [fees, setFees] = useState<FeeRecord[]>([]);
  const [facultyList, setFacultyList] = useState<FacultyMember[]>([]);
  const [timetable, setTimetable] = useState<TimetableEntry[]>([]);
  const [exams, setExams] = useState<ExamEntry[]>([]);
  const [selectedDay, setSelectedDay] = useState<string>('Monday');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [activeTab, selectedDay]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'fees') {
        const data = await api.getFees();
        setFees(data);
      } else if (activeTab === 'faculty') {
        const data = await api.getFaculty();
        setFacultyList(data);
      } else if (activeTab === 'timetable') {
        const data = await api.getTimetable('BCA', 4, selectedDay);
        setTimetable(data);
      } else if (activeTab === 'exams') {
        const data = await api.getExams('BCA', 4);
        setExams(data);
      }
    } catch (err) {
      console.error('Error loading academic data:', err);
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
            <BookOpen className="w-6 h-6 text-ait-500" />
            <span>AIT Academic Master Information</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic, Admin-verified college truth layer for Ahmedabad Institute of Technology
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center space-x-1 glass-card p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('fees')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeTab === 'fees' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <DollarSign className="w-3.5 h-3.5" />
            <span>Course Fees</span>
          </button>

          <button
            onClick={() => setActiveTab('faculty')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeTab === 'faculty' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Faculty Roster</span>
          </button>

          <button
            onClick={() => setActiveTab('timetable')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeTab === 'timetable' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Timetable</span>
          </button>

          <button
            onClick={() => setActiveTab('exams')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
              activeTab === 'exams' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Exam Schedule</span>
          </button>
        </div>
      </div>

      {/* 1. Fees Content */}
      {activeTab === 'fees' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {fees.map(f => (
            <div key={f.id} className="glass-card rounded-2xl p-6 border border-slate-800/90 relative overflow-hidden">
              <div className="flex items-center justify-between mb-3">
                <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                  {f.course_code}
                </span>
                <span className="text-xs font-mono text-slate-400">Year {f.academic_year}</span>
              </div>
              <h3 className="font-heading text-lg font-bold text-white mb-2">{f.course_name}</h3>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Tuition Fee:</span>
                  <span className="font-semibold text-white">₹{f.tuition_fee.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Exam Fee:</span>
                  <span className="font-semibold text-white">₹{f.exam_fee.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Other Charges:</span>
                  <span className="font-semibold text-white">₹{f.other_charges.toLocaleString()}</span>
                </div>
                <div className="pt-3 border-t border-slate-700/60 flex justify-between text-sm font-bold text-ait-200">
                  <span>Total Payable:</span>
                  <span>₹{f.total_fee.toLocaleString()}</span>
                </div>
              </div>
              <div className="mt-4 pt-3 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center space-x-1 text-emerald-400">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>{f.verification_status}</span>
                </span>
                <span className="font-mono">v{f.version}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 2. Faculty Content */}
      {activeTab === 'faculty' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {facultyList.map(fac => (
            <div key={fac.id} className="glass-card rounded-2xl p-6 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-ait-600 to-blue-500 flex items-center justify-center font-bold text-white text-lg">
                    {fac.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <h3 className="font-heading font-bold text-white text-base leading-tight">{fac.name}</h3>
                    <p className="text-xs text-ait-200 font-medium">{fac.designation}</p>
                    <p className="text-[11px] text-slate-400">{fac.qualification}</p>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-300">
                  <p><strong className="text-slate-400">Department:</strong> {fac.department}</p>
                  <p><strong className="text-slate-400">Office Room:</strong> {fac.office_room || 'Block B'}</p>
                  <p><strong className="text-slate-400">Office Hours:</strong> {fac.office_hours || 'Mon-Fri 2-4 PM'}</p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-700/60">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">
                  Subjects Taught:
                </span>
                <div className="flex flex-wrap gap-1">
                  {fac.subjects_taught.map((sub, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-200 border border-slate-700">
                      {sub}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 3. Timetable Content */}
      {activeTab === 'timetable' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center space-x-2 pb-2 overflow-x-auto">
            {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(day => (
              <button
                key={day}
                onClick={() => setSelectedDay(day)}
                className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  selectedDay === day
                    ? 'bg-ait-600 text-white shadow-md'
                    : 'glass-panel text-slate-400 hover:text-white'
                }`}
              >
                {day}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Time Slot</th>
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Faculty</th>
                  <th className="px-4 py-3">Room / Lab</th>
                  <th className="px-4 py-3">Division</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {timetable.map(t => (
                  <tr key={t.id} className="hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-mono text-xs text-ait-200 font-semibold">{t.start_time} - {t.end_time}</td>
                    <td className="px-4 py-3 font-medium text-white">{t.subject}</td>
                    <td className="px-4 py-3 text-slate-300">{t.faculty}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{t.room}</td>
                    <td className="px-4 py-3 font-semibold text-slate-400">Div {t.division}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Exams Content */}
      {activeTab === 'exams' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Subject Name</th>
                  <th className="px-4 py-3">Subject Code</th>
                  <th className="px-4 py-3">Exam Type</th>
                  <th className="px-4 py-3">Examination Hall</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {exams.map(e => (
                  <tr key={e.id} className="hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-bold text-white">{e.date}</td>
                    <td className="px-4 py-3 font-mono text-xs text-ait-200">{e.start_time} - {e.end_time}</td>
                    <td className="px-4 py-3 font-medium text-slate-200">{e.subject_name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{e.subject_code}</td>
                    <td className="px-4 py-3">{e.exam_type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{e.room}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        {e.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
