import React from 'react';
import Image from 'next/image';

interface CardProps {
  title: string;
  description: string;
  imageUrl?: string;
}

export default function Card({ title, description, imageUrl }: CardProps) {
  return (
    <div className="bg-card text-card-foreground rounded-xl border shadow-sm p-6 max-w-md">
      {imageUrl && (
        <Image src={imageUrl} alt={title} width={400} height={192} className="w-full h-48 object-cover rounded-lg mb-4" />
      )}
      <h2 className="text-xl font-semibold mb-2">{title}</h2>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}