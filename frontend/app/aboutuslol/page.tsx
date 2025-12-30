import React from 'react'
import mox from "@/public/mox.jpg"
import adi from "@/public/adi.jpg"
import ethan from "@/public/ethan.jpg"
import muaaz from "@/public/muaaz.jpg"
import arnav from "@/public/arnav.jpg"
import { AnimatedTestimonials } from '@/components/ui/animated-testimonials'

function AboutUs() {
    const weAre = [ 
        {
            quote: "looking black in that hot dress",
            name: "Moksh Shah",
            designation: "moxing it",
            src: mox.src,
        },
        {
      quote:
        "The attention to detail and innovative features have completely transformed our workflow. This is exactly what we've been looking for.",
      name: "Aditya Parameswar",
      designation: "Head of Web Dev at Gautam Tech Solutions",
      src: adi.src,
    },
    {
      quote:
        "Implementation was seamless and the results exceeded our expectations. The platform's flexibility is remarkable.",
      name: "Muaaz Shaikh",
      designation: "3x Google SWE Interview Reject",
      src: muaaz.src,
    },
    {
      quote:
        "This solution has significantly improved our team's productivity. The intuitive interface makes complex tasks simple.",
      name: "Ethan Mathias",
      designation: "15x Bumble Reject Streak  ",
      src: ethan.src,
    },
    {
      quote:
        "Outstanding support and robust features. It's rare to find a product that delivers on all its promises.",
      name: "Rajesh Codemarika",
      designation: "Engineering Lead at Gupta Vada Pav",
      src: arnav.src,
    },
  ];

  return (
    <div>
        <AnimatedTestimonials testimonials={weAre}/>
    </div>
  )
}

export default AboutUs
