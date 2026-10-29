// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined' && !window.ResizeObserver) {
  window.ResizeObserver = ResizeObserverMock;
}

if (typeof globalThis.jest === 'undefined' && typeof vi !== 'undefined') {
  globalThis.jest = new Proxy(vi, {
    get(target, prop, receiver) {
      if (prop === 'setTimeout') {
        return (ms) => {
          if (typeof vi.setConfig === 'function') {
            vi.setConfig({ testTimeout: ms });
          }
        };
      }
      const val = Reflect.get(target, prop, receiver);
      return typeof val === 'function' ? val.bind(target) : val;
    },
  });
}
