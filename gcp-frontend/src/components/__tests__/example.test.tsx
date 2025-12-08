import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Simple example test to verify setup works
describe('Test Setup', () => {
  it('should render a simple component', () => {
    const TestComponent = () => <div>Hello Test</div>;
    render(<TestComponent />);
    expect(screen.getByText('Hello Test')).toBeInTheDocument();
  });
});
