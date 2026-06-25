export interface Product {
  id: string;
  slug: string;
  name: string;
  subtitle: string;
  price: number;
  category: "men" | "women" | "collection";
  tag?: string;
  description: string;
  story: string;
  fabric: string;
  origin: string;
  care: string;
  sizes: string[];
  images: string[];
  colors: { name: string; hex: string }[];
  inStock: boolean;
  isNew?: boolean;
  isBestSeller?: boolean;
  shopifyVariants: Record<string, string>;
}

export const products: Product[] = [
  {
    id:          "001",
    slug:        "tailored-wool-coat",
    name:        "Tailored Wool Coat",
    subtitle:    "Architectural precision in double-faced wool",
    price:       3200,
    category:    "women",
    tag:         "New Arrival",
    description: "A study in restraint. Double-faced virgin wool structured with hand-basted canvas interlining — the coat that defines the season.",
    story:       "Conceived in our Milan atelier, cut by artisans who have spent decades mastering the single-seam shoulder. Every coat is individually finished by hand.",
    fabric:      "100% Double-Faced Virgin Wool. Lining: 100% Silk Habotai",
    origin:      "Crafted in Italy",
    care:        "Dry clean only. Store on a broad-shouldered hanger.",
    sizes:       ["XS", "S", "M", "L", "XL"],
    images: [
      "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=900&q=90",
      "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=900&q=90",
      "https://images.unsplash.com/photo-1544441893-675973e31985?w=900&q=90",
    ],
    colors:      [{ name: "Onyx", hex: "#0A0A0A" }, { name: "Ivory", hex: "#F8F7F4" }, { name: "Camel", hex: "#C19A6B" }],
    inStock:     true,
    isNew:       true,
    shopifyVariants: {
      XS: "gid://shopify/ProductVariant/59972412670286",
      S:  "gid://shopify/ProductVariant/59972412703054",
      M:  "gid://shopify/ProductVariant/59972412735822",
      L:  "gid://shopify/ProductVariant/59972412768590",
      XL: "gid://shopify/ProductVariant/59972412801358",
    },
  },
  {
    id:          "002",
    slug:        "signature-cashmere-hoodie",
    name:        "Signature Cashmere Hoodie",
    subtitle:    "Grade-A Mongolian cashmere, oversized silhouette",
    price:       1850,
    category:    "men",
    description: "The VÉRRA hoodie that rewrote luxury casualwear. Four-ply Mongolian cashmere with hand-finished ribbing and a weighted hem that falls with intention.",
    story:       "Born from a question: can effortlessness be the most refined luxury? The answer took eighteen months and three discarded prototypes.",
    fabric:      "100% Grade-A Mongolian Cashmere (4-ply)",
    origin:      "Crafted in Scotland",
    care:        "Hand wash cold or dry clean. Lay flat to dry.",
    sizes:       ["S", "M", "L", "XL", "XXL"],
    images: [
      "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=900&q=90",
      "https://images.unsplash.com/photo-1564557287817-3785e38ec1f5?w=900&q=90",
      "https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?w=900&q=90",
    ],
    colors:      [{ name: "Charcoal", hex: "#1B1B1B" }, { name: "Bone", hex: "#E8E0D0" }, { name: "Mushroom", hex: "#9B8B79" }],
    inStock:     true,
    isBestSeller: true,
    shopifyVariants: {
      S:   "gid://shopify/ProductVariant/59972413522254",
      M:   "gid://shopify/ProductVariant/59972413555022",
      L:   "gid://shopify/ProductVariant/59972413587790",
      XL:  "gid://shopify/ProductVariant/59972413620558",
      XXL: "gid://shopify/ProductVariant/59972413653326",
    },
  },
  {
    id:          "003",
    slug:        "italian-leather-jacket",
    name:        "Italian Leather Jacket",
    subtitle:    "Nappa leather, moto-influenced architecture",
    price:       5400,
    category:    "men",
    tag:         "Iconic",
    description: "Vegetable-tanned nappa leather from a fourth-generation Florentine tannery. The biker silhouette deconstructed and rebuilt for an era that demands both beauty and durability.",
    story:       "We spent a year finding leather with enough character to age beautifully, soft enough to feel like a second skin from day one.",
    fabric:      "Full-grain vegetable-tanned Nappa leather. Lining: 100% Viscose",
    origin:      "Crafted in Florence, Italy",
    care:        "Apply quality leather conditioner every 6 months. Store away from direct light.",
    sizes:       ["XS", "S", "M", "L", "XL"],
    images: [
      "https://images.unsplash.com/photo-1521223890158-f9f7c3d5d504?w=900&q=90",
      "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=900&q=90",
      "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=900&q=90",
    ],
    colors:      [{ name: "Noir", hex: "#0A0A0A" }, { name: "Cognac", hex: "#7B4E2D" }],
    inStock:     true,
    shopifyVariants: {
      XS: "gid://shopify/ProductVariant/59972413915470",
      S:  "gid://shopify/ProductVariant/59972413948238",
      M:  "gid://shopify/ProductVariant/59972413981006",
      L:  "gid://shopify/ProductVariant/59972414013774",
      XL: "gid://shopify/ProductVariant/59972414046542",
    },
  },
  {
    id:          "004",
    slug:        "silk-wide-trousers",
    name:        "Silk Wide-Leg Trousers",
    subtitle:    "Charmeuse silk, palazzo silhouette",
    price:       1290,
    category:    "women",
    tag:         "New Arrival",
    description: "A fluid fall. Washed silk charmeuse with a high waist and generous palazzo leg — the trouser that moves like water and photographs like light.",
    story:       "The result of a single obsession: find the silk that drapes exactly the way we imagined. We found it at a mill in Como that has been weaving since 1873.",
    fabric:      "100% Washed Silk Charmeuse (Como, Italy)",
    origin:      "Crafted in Italy",
    care:        "Dry clean or gentle hand wash cold. Iron on low, reverse side.",
    sizes:       ["XS", "S", "M", "L"],
    images: [
      "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=900&q=90",
      "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=900&q=90",
      "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=900&q=90",
    ],
    colors:      [{ name: "Ivory", hex: "#F8F7F4" }, { name: "Midnight", hex: "#1a1a2e" }, { name: "Sand", hex: "#C2A882" }],
    inStock:     true,
    isNew:       true,
    shopifyVariants: {
      XS: "gid://shopify/ProductVariant/59972414538062",
      S:  "gid://shopify/ProductVariant/59972414570830",
      M:  "gid://shopify/ProductVariant/59972414603598",
      L:  "gid://shopify/ProductVariant/59972414636366",
    },
  },
  {
    id:          "005",
    slug:        "premium-overshirt",
    name:        "Premium Overshirt",
    subtitle:    "Brushed heavy cotton twill, relaxed fit",
    price:       690,
    category:    "men",
    description: "Utility elevated to art form. 380gsm brushed cotton twill with military-inspired detailing and a silhouette that works over everything from shirting to knitwear.",
    story:       "We challenged ourselves to make the most wearable piece in the collection. Six months of testing different weights and washes until this felt inevitable.",
    fabric:      "100% Brushed Cotton Twill (380gsm)",
    origin:      "Crafted in Portugal",
    care:        "Machine wash cold. Tumble dry low. Iron medium heat.",
    sizes:       ["S", "M", "L", "XL", "XXL"],
    images: [
      "https://images.unsplash.com/photo-1503341504253-dff4815485f1?w=900&q=90",
      "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=900&q=90",
      "https://images.unsplash.com/photo-1532453288672-3a27e9be9efd?w=900&q=90",
    ],
    colors:      [{ name: "Slate", hex: "#475569" }, { name: "Espresso", hex: "#3B1F0E" }, { name: "Sage", hex: "#7C9070" }],
    inStock:     true,
    isBestSeller: true,
    shopifyVariants: {
      S:   "gid://shopify/ProductVariant/59972414800206",
      M:   "gid://shopify/ProductVariant/59972414832974",
      L:   "gid://shopify/ProductVariant/59972414865742",
      XL:  "gid://shopify/ProductVariant/59972414898510",
      XXL: "gid://shopify/ProductVariant/59972414931278",
    },
  },
  {
    id:          "006",
    slug:        "luxury-knitwear-vest",
    name:        "Luxury Knitwear Vest",
    subtitle:    "Double-gauge merino rib, relaxed fit",
    price:       940,
    category:    "women",
    description: "The vest that defines the modern wardrobe. Double-gauge merino knit with a relaxed body and precision-linked seams. Wears over shirts, under coats, and alone with equal authority.",
    story:       "Knitted on 1940s-era flat-bed machines in a family workshop in the Scottish Borders. Each piece takes six hours.",
    fabric:      "100% Extra-Fine Merino Wool (19.5 micron)",
    origin:      "Crafted in Scotland",
    care:        "Hand wash cold with specialist wool detergent. Dry flat.",
    sizes:       ["XS", "S", "M", "L", "XL"],
    images: [
      "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=900&q=90",
      "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=900&q=90",
      "https://images.unsplash.com/photo-1583744946564-b52ac1c389c8?w=900&q=90",
    ],
    colors:      [{ name: "Ecru", hex: "#E8E0D0" }, { name: "Black", hex: "#0A0A0A" }, { name: "Bordeaux", hex: "#5C1A1A" }],
    inStock:     true,
    isNew:       true,
    shopifyVariants: {
      XS: "gid://shopify/ProductVariant/59972415291726",
      S:  "gid://shopify/ProductVariant/59972415324494",
      M:  "gid://shopify/ProductVariant/59972415357262",
      L:  "gid://shopify/ProductVariant/59972415390030",
      XL: "gid://shopify/ProductVariant/59972415422798",
    },
  },
];

export const journalPosts = [
  {
    id:       "j1",
    slug:     "the-quiet-revolution-of-less",
    category: "Style",
    title:    "The Quiet Revolution of Less",
    excerpt:  "On the steady displacement of maximalism — and why the most powerful statement a garment can make is restraint.",
    date:     "December 2025",
    readTime: "7 min",
    image:    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=900&q=90",
    author:   "Édith Moreau",
  },
  {
    id:       "j2",
    slug:     "inside-the-como-silk-mills",
    category: "Craftsmanship",
    title:    "Inside the Como Silk Mills",
    excerpt:  "A visit to the 150-year-old weaving workshop where VÉRRA sources its silk charmeuse. Three generations, one obsession.",
    date:     "November 2025",
    readTime: "12 min",
    image:    "https://images.unsplash.com/photo-1558171813-c28e4e92ee8d?w=900&q=90",
    author:   "Marco Cipriani",
  },
  {
    id:       "j3",
    slug:     "on-wearing-art-in-venice",
    category: "Travel",
    title:    "On Wearing Art in Venice",
    excerpt:  "The city that demands your full aesthetic attention. A guide to dressing through the Biennale with intention.",
    date:     "October 2025",
    readTime: "9 min",
    image:    "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?w=900&q=90",
    author:   "Sofia Andreotti",
  },
  {
    id:       "j4",
    slug:     "the-new-luxury-of-slowness",
    category: "Culture",
    title:    "The New Luxury of Slowness",
    excerpt:  "When speed became the dominant currency of culture, luxury repositioned itself around something far more radical: time itself.",
    date:     "September 2025",
    readTime: "6 min",
    image:    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=900&q=90",
    author:   "Édith Moreau",
  },
];

export function getProductBySlug(slug: string): Product | undefined {
  return products.find((p) => p.slug === slug);
}

export function getProductsByCategory(category: "men" | "women" | "collection"): Product[] {
  return products.filter((p) => p.category === category);
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-GB", {
    style:    "currency",
    currency: "GBP",
    minimumFractionDigits: 0,
  }).format(price);
}
