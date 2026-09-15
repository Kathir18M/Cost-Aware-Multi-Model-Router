import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="content" style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <div className="glass-panel form-box" style={{ width: "min(100%, 480px)" }}>
        <div className="kicker">/ AUTH</div>
        <h1 className="title">Create account</h1>
        <SignUp routing="hash" signInUrl="/sign-in" />
      </div>
    </main>
  );
}
