import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CronBuilder from '../components/CronBuilder'

describe('CronBuilder', () => {
  it('applies a preset when selected', async () => {
    const onChange = vi.fn()
    render(<CronBuilder value="0 9 * * *" onChange={onChange} />)
    await userEvent.selectOptions(screen.getByLabelText('preset'), '0 9 * * 1')
    expect(onChange).toHaveBeenCalledWith('0 9 * * 1')
  })

  it('edits individual cron fields', async () => {
    const onChange = vi.fn()
    render(<CronBuilder value="0 9 * * *" onChange={onChange} />)
    fireEvent.change(screen.getByLabelText('hour'), { target: { value: '12' } })
    expect(onChange).toHaveBeenCalledWith('0 12 * * *')
  })
})
