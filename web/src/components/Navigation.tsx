"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import UserMenu from "@/components/UserMenu";

const navItems = [
  { href: "/", label: "Rankings" },
  { href: "/face-to-face", label: "Face to Face" },
  { href: "/similarity-search", label: "Similarity" },
  { href: "/team-analysis", label: "Team Analysis" },
  { href: "/team-rankings", label: "Team Rankings" },
  { href: "/national-teams", label: "National Teams" },
  { href: "/talent-pool", label: "Talent Pool" },
  { href: "/demands", label: "Demands" },
];

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <span className="text-xl font-bold text-navy">The Scouting Arena</span>
          </Link>

          {/* Right side: Navigation + User Menu + Mobile Menu Button */}
          <div className="flex items-center gap-3 ml-auto">
            {/* Desktop Navigation Links - hidden on mobile/tablet */}
            <div className="hidden lg:flex items-center space-x-2">
              {navItems.map((item) => (
                <Button
                  key={item.href}
                  asChild
                  variant="ghost"
                  className="text-sm px-3"
                >
                  <Link href={item.href}>{item.label}</Link>
                </Button>
              ))}
            </div>
            {/* User Menu - visible on all screen sizes */}
            <UserMenu />

            {/* Mobile Menu Button - visible on mobile/tablet */}
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Menu - visible when open */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-200 py-4">
            <div className="flex flex-col space-y-2">
              {navItems.map((item) => (
                <Button
                  key={item.href}
                  asChild
                  variant="ghost"
                  className="justify-start text-base"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Link href={item.href}>{item.label}</Link>
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
