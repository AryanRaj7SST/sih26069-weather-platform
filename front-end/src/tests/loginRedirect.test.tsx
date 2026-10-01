// @vitest-environment jsdom

import React from "react";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MemoryRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import type { UserProfile } from "@/services/authApi";
import { LoginPage } from "@/pages/LoginPage";
import { GuestOnlyRoute } from "@/components/auth/GuestOnlyRoute";
import { useAuth } from "@/context/AuthContext";

vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

type LoginEntry =
  | string
  | {
      pathname: string;
      state?: { from?: { pathname?: string } };
    };

function renderLogin(
  role: UserProfile["role"],
  initialEntry: LoginEntry = "/login",
) {
  mockedUseAuth.mockReturnValue({
    token: "token",
    user: { role } as UserProfile,
    operator: null,
    isAuthenticated: true,
    isOperator: role === "OPERATOR" || role === "ADMIN",
    isCitizen: role === "CITIZEN",
    isAdmin: role === "ADMIN",
    isLoading: false,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    updateSavedLocation: vi.fn(),
  });

  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route element={<GuestOnlyRoute />}>
          <Route
            path="/login"
            element={
              <>
                <LoginPage />
                <LocationProbe />
              </>
            }
          />
        </Route>
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LoginPage authenticated redirects", () => {
  it.each([
    ["ADMIN", "/dashboard"],
    ["OPERATOR", "/admin/queue"],
    ["CITIZEN", "/citizen-dashboard"],
  ] as const)(
    "redirects an authenticated %s user to %s",
    async (role, destination) => {
      const view = renderLogin(role);

      await waitFor(() => {
        expect(view.getByTestId("location").textContent).toBe(destination);
      });
    },
  );

  it("preserves a protected deep-link destination", async () => {
    mockedUseAuth.mockReturnValue({
      token: "token",
      user: { role: "ADMIN" } as UserProfile,
      operator: null,
      isAuthenticated: true,
      isOperator: true,
      isCitizen: false,
      isAdmin: true,
      isLoading: false,
      login: vi.fn(),
      signup: vi.fn(),
      logout: vi.fn(),
      updateSavedLocation: vi.fn(),
    });

    const view = render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route
            path="/protected"
            element={
              <Navigate
                to="/login"
                state={{ from: { pathname: "/incidents/incident-123" } }}
                replace
              />
            }
          />
          <Route element={<GuestOnlyRoute />}>
            <Route
              path="/login"
              element={
                <>
                  <LoginPage />
                  <LocationProbe />
                </>
              }
            />
          </Route>
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(view.getByTestId("location").textContent).toBe(
        "/incidents/incident-123",
      );
    });
  });
});
