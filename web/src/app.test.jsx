import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { App } from './main.jsx';

const dashboard = { roles: [{ 'Job title': 'Data Scientist', Categories: 'Data Science', 'Catalog rows': 12 }, { 'Job title': 'Office Manager', Categories: 'Operations', 'Catalog rows': 3 }], categories: ['Data Science', 'Operations'], catalog_skill_demand: [{ skill: 'Python', catalog_mentions: 10 }], progress: { saved_plan_count: 0, completed_step_count: 0, tracked_step_count: 0, completion_ratio: 0, completed_tracked_step_count: 0, untracked_plan_count: 0 } };
const analysis = { role: { title: 'Data Scientist', category: 'Data Science' }, title_match: { method: 'exact', relevance: 1 }, compatibility: 72.5, signals: { skill_coverage: .5, keyword_similarity: .42, semantic_similarity: .7 }, caveat: 'Prototype estimate, not a hiring probability.', matched_skills: ['Python'], missing_skills: ['SQL'], priority: [{ Skill: 'SQL', 'Demand Score': .8, Priority: 'High' }], recommendations: [{ Skill: 'SQL', Rank: 1, Explanation: 'Catalog demand', Resources: [] }], roadmap: ['SQL'], learning_plan: [{ Day: 30, Phase: 'First 30 days', Skills: ['SQL'] }], completed_skills: [] };
function response(body, ok = true) { return { ok, json: async () => body }; }

describe('SkillScope frontend flows', () => {
  beforeEach(() => { global.fetch = vi.fn().mockResolvedValue(response(dashboard)); });
  afterEach(() => cleanup());

  it('loads real dashboard summaries and filters job profiles by catalog category', async () => {
    render(<App/>);
    expect(await screen.findByText('Turn your skills into your next opportunity.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Explore jobs' }));
    expect(await screen.findByText('Data Scientist')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Search job titles'), { target: { value: 'nonexistent' } });
    expect(screen.getByText('No roles match those filters')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Filter by catalog category'), { target: { value: 'Operations' } });
    fireEvent.change(screen.getByLabelText('Search job titles'), { target: { value: '' } });
    expect(screen.getByText('Office Manager')).toBeInTheDocument();
    expect(screen.queryByText('Data Scientist')).not.toBeInTheDocument();
  });

  it('uploads a resume and shows the API skill gap results', async () => {
    global.fetch.mockResolvedValueOnce(response(dashboard)).mockResolvedValueOnce(response(analysis));
    render(<App/>);
    fireEvent.click(await screen.findByRole('button', { name: /Resume analysis/i }));
    const file = new File(['A Python and data analysis resume with enough text to pass the extraction threshold for the analyzer.'], 'resume.txt', { type: 'text/plain' });
    fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText('Target job title'), { target: { value: 'Data Scientist' } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze my resume/i }));
    expect(await screen.findByText('Your match for Data Scientist')).toBeInTheDocument();
    expect(screen.getAllByText('SQL').length).toBeGreaterThan(0);
    expect(screen.getByText('72.5%')).toBeInTheDocument();
  });

  it('shows API errors without losing the analysis form', async () => {
    global.fetch.mockResolvedValueOnce(response(dashboard)).mockResolvedValueOnce(response({ detail: 'No sufficiently relevant catalog job title was found.' }, false));
    render(<App/>);
    fireEvent.click(await screen.findByRole('button', { name: /Resume analysis/i }));
    const file = new File(['A Python and data analysis resume with enough text to pass the extraction threshold.'], 'resume.txt', { type: 'text/plain' });
    fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText('Target job title'), { target: { value: 'Unknown role' } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze my resume/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No sufficiently relevant catalog job title');
    expect(screen.getByText('Analyze my resume')).toBeInTheDocument();
  });

  it('saves roadmap completion and refreshes progress', async () => {
    global.fetch.mockResolvedValueOnce(response(dashboard)).mockResolvedValueOnce(response(analysis)).mockResolvedValueOnce(response({ completed_skills: ['SQL'], progress: { saved_plan_count: 1, completed_step_count: 1, tracked_step_count: 1, completed_tracked_step_count: 1, completion_ratio: 1, untracked_plan_count: 0 } })).mockResolvedValueOnce(response({ ...dashboard, progress: { ...dashboard.progress, saved_plan_count: 1, completed_step_count: 1, tracked_step_count: 1, completed_tracked_step_count: 1, completion_ratio: 1 } }));
    render(<App/>);
    fireEvent.click(await screen.findByRole('button', { name: /Resume analysis/i }));
    fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [new File(['A Python and data analysis resume with enough text for this analysis request.'], 'resume.txt', { type: 'text/plain' })] } });
    fireEvent.change(screen.getByLabelText('Target job title'), { target: { value: 'Data Scientist' } });
    fireEvent.click(screen.getByRole('button', { name: /Analyze my resume/i }));
    await screen.findByText('Your match for Data Scientist');
    fireEvent.click(screen.getByRole('button', { name: 'Learning roadmap' }));
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /Save progress/i }));
    expect(await screen.findByRole('button', { name: /Saved/i })).toBeInTheDocument();
    const progressCall = global.fetch.mock.calls.find(([url]) => url === '/api/progress');
    expect(JSON.parse(progressCall[1].body).completed_skills).toEqual(['SQL']);
  });
});

