"use client";

import {
  SignInButton,
  SignUpButton,
  UserButton,
  useUser,
} from "@clerk/nextjs";

export default function AppHeader() {
  const { user, isLoaded } = useUser();

  if (!isLoaded) {
    return <div style={{ color: "#cbd5e1", marginBottom: 12 }}>Loading authentication…</div>;
  }

  return (
    <div style={{ display: "grid", gap: 12, marginBottom: 8 }}>
      {!user ? (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <SignInButton mode="modal">
            <button type="button" className="secondary-button">Sign In</button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button" className="primary-button">Sign Up</button>
          </SignUpButton>
        </div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          <UserButton />
          <div style={{ color: "#e2e8f0", fontSize: 13, lineHeight: 1.5 }}>
            <div>{user.firstName ?? user.emailAddresses[0]?.emailAddress?.split("@")[0] ?? "User"}</div>
            <div style={{ color: "#cbd5e1" }}>{user.emailAddresses[0]?.emailAddress ?? "Authenticated user"}</div>
          </div>
        </div>
      )}
    </div>
  );
}
