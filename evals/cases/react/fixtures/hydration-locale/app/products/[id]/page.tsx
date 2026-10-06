import { Price } from './price';

type Product = { id: string; name: string; amountCents: number; currency: string };

async function getProduct(id: string): Promise<Product> {
  const res = await fetch(`${process.env.API_URL}/products/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`product ${id}: ${res.status}`);
  return res.json();
}

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const product = await getProduct(id);
  return (
    <main>
      <h1>{product.name}</h1>
      <Price amountCents={product.amountCents} currency={product.currency} />
    </main>
  );
}
