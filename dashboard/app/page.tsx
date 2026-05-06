// dashboard/app/page.tsx — Redirect root to /status
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/status");
}
