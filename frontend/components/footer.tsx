import React from 'react'
import Link from 'next/link'
function Footer() {
  return (
    <footer className="bg-neutral-900 text-white p-12 mt-20">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="md:col-span-2">
              <h3 className="text-xl font-semibold mb-2">Ra.AI</h3>
              <p className="text-sm text-gray-400 max-w-sm">
                Unlock your emotional intelligence. From self-awareness to social mastery, our platform is your guide to a more connected and resilient you.
              </p>
            </div>
            <div>
              <h4 className="text-md font-medium mb-3">Useful</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><Link href="#" className="hover:underline">Manifesto</Link></li>
                <li><Link href="#" className="hover:underline">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-md font-medium mb-3">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><Link href="#" className="hover:underline">Privacy Policy</Link></li>
                <li><Link href="#" className="hover:underline">Terms & Conditions</Link></li>
              </ul>
            </div>
          </div>
          <div className="text-center text-gray-500 text-xs mt-12">
            &copy; {new Date().getFullYear()} Ra.AI. All rights reserved.
          </div>
        </footer>
  )
}

export default Footer