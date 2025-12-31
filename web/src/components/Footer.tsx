import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-gray-800 bg-[#0B1B3F] mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="space-y-3 md:col-span-2">
            <h3 className="text-lg font-semibold text-white font-poppins">
              The Scouting Arena
            </h3>
            <p className="text-sm text-gray-400">
              Advanced football analytics & player scouting platform
            </p>
          </div>

          {/* Contact */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-white uppercase tracking-wider">
              Contact
            </h4>
            <div className="space-y-2">
              <a
                href="mailto:thescoutingarena@gmail.com"
                className="text-sm text-gray-400 hover:text-[#00FF88] transition-colors flex items-center gap-2"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
                thescoutingarena@gmail.com
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-4 pt-4">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-500">
              © {new Date().getFullYear()} The Scouting Arena. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
