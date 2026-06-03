import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import TeamPage from '../components/TeamPage'
import { LanguageProvider } from '../context/LanguageContext'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

function renderWithProviders(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('TeamPage - No Teams', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('shows create/join UI when user has no teams', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ teams: [] }),
    })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText('Create a Team')).toBeInTheDocument()
      expect(screen.getByText('Join a Team')).toBeInTheDocument()
    })
  })

  it('shows "Your Team Workspace" heading when no teams', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ teams: [] }),
    })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText('Your Team Workspace')).toBeInTheDocument()
    })
  })

  it('shows loading spinner initially', () => {
    // Never resolve — keep loading
    mockFetch.mockImplementation(() => new Promise(() => {}))

    renderWithProviders(<TeamPage />)

    // Check for spinner
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeTruthy()
  })
})

describe('TeamPage - With Teams', () => {
  const mockTeams = {
    teams: [
      { team_id: 'team-1', name: 'Alpha Team', my_role: 'owner' },
    ]
  }

  const mockTeamInfo = {
    in_team: true,
    team_id: 'team-1',
    name: 'Alpha Team',
    description: 'Our test team',
    my_role: 'owner',
    invite_code: 'abc123def456',
    members: [
      { user_id: 1, username: 'Alice', role: 'owner' },
      { user_id: 2, username: 'Bob', role: 'member' },
    ],
  }

  const mockRequests = {
    requests: [
      {
        id: 'req-1',
        user_id: 1,
        username: 'Alice',
        title: 'Build a dashboard',
        description: 'We need a data dashboard',
        status: 'pending',
        linked_task_id: null,
        duplicate_of: null,
        reviewer_notes: '',
        code: '',
        created_at: '2026-05-31T00:00:00Z',
        updated_at: '2026-05-31T00:00:00Z',
      },
      {
        id: 'req-2',
        user_id: 2,
        username: 'Bob',
        title: 'Add login page',
        description: 'Login with email',
        status: 'approved',
        linked_task_id: null,
        duplicate_of: null,
        reviewer_notes: '',
        code: '',
        created_at: '2026-05-30T00:00:00Z',
        updated_at: '2026-05-31T00:00:00Z',
      },
    ]
  }

  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('shows team name and stats', async () => {
    // First call: list teams, second: team info, third: requests
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeams })
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeamInfo })
      .mockResolvedValueOnce({ ok: true, json: async () => mockRequests })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText('Alpha Team')).toBeInTheDocument()
    })
    expect(screen.getByText('2 members')).toBeInTheDocument()
    expect(screen.getByText('2 requests')).toBeInTheDocument()
    expect(screen.getByText('1 pending')).toBeInTheDocument()
  })

  it('shows request board tab with request count', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeams })
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeamInfo })
      .mockResolvedValueOnce({ ok: true, json: async () => mockRequests })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText(/Request Board/)).toBeInTheDocument()
    })
  })

  it('shows members tab with correct count', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeams })
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeamInfo })
      .mockResolvedValueOnce({ ok: true, json: async () => mockRequests })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText(/2 members/)).toBeInTheDocument()
    })
  })

  it('shows invite code for owner', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeams })
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeamInfo })
      .mockResolvedValueOnce({ ok: true, json: async () => mockRequests })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText('abc123def456')).toBeInTheDocument()
    })
  })

  it('shows "No feature requests yet" when requests empty', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeams })
      .mockResolvedValueOnce({ ok: true, json: async () => mockTeamInfo })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ requests: [] }) })

    renderWithProviders(<TeamPage />)

    await waitFor(() => {
      expect(screen.getByText('No feature requests yet.')).toBeInTheDocument()
    })
  })
})
