import React, { useState } from 'react';
import { BookOpen, Sparkles, CheckCircle, Brain, Target, RotateCcw, Award } from 'lucide-react';

export const StudyCenterView: React.FC = () => {
  const [activeModule, setActiveModule] = useState<'quiz' | 'flashcards' | 'planner'>('quiz');
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [activeFlashcard, setActiveFlashcard] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const quizQuestions = [
    {
      q: 'Which normal form eliminates partial dependencies where non-prime attributes depend on a part of candidate key?',
      options: ['1NF (First Normal Form)', '2NF (Second Normal Form)', '3NF (Third Normal Form)', 'BCNF (Boyce-Codd NF)'],
      correct: 1,
    },
    {
      q: 'In relational database transactions, what does the "I" in ACID stand for?',
      options: ['Integration', 'Isolation', 'Integrity', 'Indexing'],
      correct: 1,
    },
    {
      q: 'What is the time complexity of searching a node in a balanced Binary Search Tree (BST)?',
      options: ['O(1)', 'O(n)', 'O(log n)', 'O(n log n)'],
      correct: 2,
    },
  ];

  const flashcards = [
    {
      term: 'ACID Properties',
      definition: 'Atomicity (all or nothing), Consistency (preserves database rules), Isolation (concurrent execution without interference), Durability (committed changes persist).',
    },
    {
      term: 'B-Tree & B+ Tree Indexing',
      definition: 'Self-balancing search trees used heavily in SQL database engines (PostgreSQL/MySQL) for fast O(log N) disk-based record lookups and range queries.',
    },
    {
      term: 'Boyce-Codd Normal Form (BCNF)',
      definition: 'A stricter version of 3NF where for every functional dependency X -> Y, X must be a super key of the relation table.',
    },
  ];

  const handleSelectOption = (qIdx: number, optIdx: number) => {
    setSelectedAnswers(prev => ({ ...prev, [qIdx]: optIdx }));
  };

  const handleCalculateScore = () => {
    let score = 0;
    quizQuestions.forEach((q, i) => {
      if (selectedAnswers[i] === q.correct) score += 1;
    });
    setQuizScore(score);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="font-heading text-2xl font-bold text-white flex items-center space-x-2">
            <Brain className="w-6 h-6 text-ait-500" />
            <span>AIT AI Study Center & Exam Coach</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Personalized exam preparation, interactive quizzes, and syllabus revision flashcards
          </p>
        </div>

        {/* Module Switcher */}
        <div className="flex items-center space-x-1 glass-card p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveModule('quiz')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeModule === 'quiz' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Practice Quiz
          </button>
          <button
            onClick={() => setActiveModule('flashcards')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeModule === 'flashcards' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Flashcards
          </button>
        </div>
      </div>

      {/* Quiz Module */}
      {activeModule === 'quiz' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h3 className="font-heading text-lg font-bold text-white">DBMS & Computer Science Quiz</h3>
              <p className="text-xs text-slate-400">Curated for BCA Semester 4 Mid-Term Examinations</p>
            </div>
            {quizScore !== null && (
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold">
                <Award className="w-4 h-4" />
                <span>Score: {quizScore} / {quizQuestions.length}</span>
              </div>
            )}
          </div>

          <div className="space-y-6">
            {quizQuestions.map((q, qIdx) => (
              <div key={qIdx} className="space-y-3">
                <p className="text-sm font-semibold text-slate-200">
                  {qIdx + 1}. {q.q}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {q.options.map((opt, optIdx) => {
                    const isSelected = selectedAnswers[qIdx] === optIdx;
                    const isSubmitted = quizScore !== null;
                    const isCorrect = q.correct === optIdx;

                    let btnStyle = 'glass-panel text-slate-300 hover:text-white border-slate-800';
                    if (isSelected) btnStyle = 'bg-ait-600/40 text-white border-ait-500';
                    if (isSubmitted) {
                      if (isCorrect) btnStyle = 'bg-emerald-500/30 text-emerald-200 border-emerald-500';
                      else if (isSelected && !isCorrect) btnStyle = 'bg-red-500/30 text-red-200 border-red-500';
                    }

                    return (
                      <button
                        key={optIdx}
                        onClick={() => handleSelectOption(qIdx, optIdx)}
                        className={`p-3 rounded-xl text-left text-xs font-medium border transition-all ${btnStyle}`}
                      >
                        {opt}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
            <button
              onClick={() => {
                setSelectedAnswers({});
                setQuizScore(null);
              }}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
            <button
              onClick={handleCalculateScore}
              className="px-5 py-2 rounded-xl bg-ait-600 hover:bg-ait-500 text-white text-xs font-semibold shadow-lg shadow-ait-600/30 transition-all hover:scale-105"
            >
              Submit & Check Answers
            </button>
          </div>
        </div>
      )}

      {/* Flashcards Module */}
      {activeModule === 'flashcards' && (
        <div className="glass-card rounded-3xl p-8 border border-slate-800 text-center space-y-6">
          <div className="text-xs font-mono text-slate-400">
            Card {activeFlashcard + 1} of {flashcards.length}
          </div>

          <div
            onClick={() => setFlipped(!flipped)}
            className="h-56 glass-panel rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer border border-slate-700/80 hover:border-ait-500/50 transition-all shadow-xl select-none"
          >
            {!flipped ? (
              <div>
                <Sparkles className="w-6 h-6 text-ait-gold mx-auto mb-2" />
                <h3 className="font-heading text-xl font-bold text-white mb-2">
                  {flashcards[activeFlashcard].term}
                </h3>
                <p className="text-xs text-slate-400">Click to reveal definition</p>
              </div>
            ) : (
              <div>
                <CheckCircle className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-slate-200 leading-relaxed max-w-lg">
                  {flashcards[activeFlashcard].definition}
                </p>
                <p className="text-xs text-slate-400 mt-3">Click to flip back</p>
              </div>
            )}
          </div>

          <div className="flex items-center justify-center space-x-3">
            <button
              onClick={() => {
                setFlipped(false);
                setActiveFlashcard(prev => (prev > 0 ? prev - 1 : flashcards.length - 1));
              }}
              className="px-4 py-2 rounded-xl glass-panel text-xs font-semibold text-slate-300 hover:text-white"
            >
              Previous Card
            </button>
            <button
              onClick={() => {
                setFlipped(false);
                setActiveFlashcard(prev => (prev < flashcards.length - 1 ? prev + 1 : 0));
              }}
              className="px-4 py-2 rounded-xl bg-ait-600 hover:bg-ait-500 text-xs font-semibold text-white shadow-lg shadow-ait-600/30"
            >
              Next Card
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
