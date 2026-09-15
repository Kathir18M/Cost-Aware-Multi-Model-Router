import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <main className="content" style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <div className="glass-panel form-box" style={{ width: "min(100%, 480px)" }}>
        <div className="kicker">/ AUTH</div>
        <h1 className="title">Sign in</h1>
        <SignIn routing="hash" signUpUrl="/sign-up" />
      </div>
    </main>
  );
}
