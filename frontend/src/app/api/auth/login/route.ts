import { NextResponse } from "next/server";

interface LoginRequestBody {
  email?: string;
  password?: string;
}

interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
  };
}

const BACKEND_URL =
  process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000/api";
const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as LoginRequestBody;
    const email = (body.email || "").trim().toLowerCase();
    const password = body.password || "";

    let backendRes: Response;
    try {
      backendRes = await fetch(`${BACKEND_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      return NextResponse.json(
        {
          detail:
            "Cannot connect to Backend FastAPI server (http://127.0.0.1:8000). Please ensure the Python server is running.",
        },
        { status: 500 }
      );
    }

    if (!backendRes.ok) {
      return NextResponse.json(
        { detail: "Incorrect email or password" },
        { status: backendRes.status }
      );
    }

    const data = (await backendRes.json()) as BackendTokenResponse;
    const response = NextResponse.json({
      success: true,
      access_token: data.access_token,
      user: data.user,
    });

    const isHttps =
      request.url.startsWith("https://") ||
      request.headers.get("x-forwarded-proto") === "https";

    response.cookies.set("session_token", data.access_token, {
      httpOnly: true,
      secure: isHttps,
      sameSite: "lax",
      path: "/",
      maxAge: SEVEN_DAYS_SECONDS,
    });

    return response;
  } catch {
    return NextResponse.json(
      { detail: "Invalid login payload" },
      { status: 400 }
    );
  }
}
